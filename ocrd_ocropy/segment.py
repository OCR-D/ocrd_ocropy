from __future__ import absolute_import

# pylint: disable=import-error
# pylint: disable=unused-import
# pylint: disable=wrong-import-position
# pylint: disable=wrong-import-order
# pylint: disable=multiple-statements

from ocrd import Processor
from ocrd_utils import (
    getLogger,
    concat_padded,
    polygon_from_points,
    points_from_x0y0x1y1,
    MIMETYPE_PAGE
)

from ocrd_models.ocrd_page import TextRegionType, TextLineType, CoordsType, to_xml
from ocrd_modelfactory import page_from_file
from ocrd_ocropy.config import OCRD_TOOL

import logging
logging.getLogger('matplotlib').setLevel(logging.INFO)

import numpy as np
import matplotlib
matplotlib.use('Agg')

from scipy.ndimage.filters import gaussian_filter, uniform_filter, maximum_filter

import ocrolib
from ocrolib import psegutils, morph, sl

log = getLogger('processor.ocropySegment')

def find(condition):
    "Return the indices where ravel(condition) is true"
    res, = np.nonzero(np.ravel(condition))
    return res

def norm_max(v):
    return v/np.amax(v)

def B(a):
    if a.dtype == np.dtype('B'):
        return a
    return np.array(a, 'B')


class OcropySegment(Processor):

    # Snippety snap from `which ocropus-gpageseg`
    #-------- 8< --------------

    def compute_gradmaps(self, binary, scale):
        # use gradient filtering to find baselines
        boxmap = psegutils.compute_boxmap(binary, scale)
        cleaned = boxmap * binary
        if self.parameter['usegauss']:
            # this uses Gaussians
            grad = gaussian_filter(1.0 * cleaned, (self.parameter['vscale']*0.3 * scale,
                                                   self.parameter['hscale']*6 * scale), order=(1, 0))
        else:
            # this uses non-Gaussian oriented filters
            grad = gaussian_filter(1.0 * cleaned, (max(4, self.parameter['vscale']*0.3 * scale),
                                                   self.parameter['hscale']*scale), order=(1, 0))
            grad = uniform_filter(grad, (self.parameter['vscale'], self.parameter['hscale']*6 * scale))
        bottom = ocrolib.norm_max((grad < 0) * (-1 * grad))
        top = ocrolib.norm_max((grad > 0) * grad)
        return bottom, top, boxmap


    def compute_line_seeds(self, binary, bottom, top, colseps, scale):
        """Base on gradient maps, computes candidates for baselines
        and xheights.  Then, it marks the regions between the two
        as a line seed."""
        t = self.parameter['threshold']
        vrange = int(self.parameter['vscale']*scale)
        bmarked = maximum_filter(bottom == maximum_filter(bottom, (vrange, 0)), (2, 2))
        bmarked = bmarked * (bottom > t * np.amax(bottom) * t) * (1-colseps)
        tmarked = maximum_filter(top == maximum_filter(top, (vrange, 0)), (2, 2))
        tmarked = tmarked * (top > t * np.amax(top) * t/2) * (1-colseps)
        tmarked = maximum_filter(tmarked, (1, 20))
        seeds = np.zeros(binary.shape, 'i')
        delta = max(3, int(scale/2))
        for x in range(bmarked.shape[1]):
            transitions = sorted([(y, 1) for y in find(bmarked[:, x])] + [(y, 0) for y in find(tmarked[:, x])])[::-1]
            transitions += [(0, 0)]
            for l in range(len(transitions)-1):
                y0, s0 = transitions[l]
                if s0 == 0: continue
                seeds[y0-delta:y0, x] = 1
                y1, s1 = transitions[l+1]
                if s1 == 0 and (y0-y1) < 5 * scale: seeds[y1:y0, x] = 1
        seeds = maximum_filter(seeds, (1, int(1+scale)))
        seeds = seeds * (1 - colseps)
        seeds, _ = morph.label(seeds)
        return seeds



    def compute_colseps_morph(self, binary, scale):
        """Finds extended vertical whitespace corresponding to column separators
        using morphological operations."""
        boxmap = psegutils.compute_boxmap(binary, scale, dtype='B')
        bounds = morph.rb_closing(B(boxmap), (int(5 * scale), int(5 * scale)))
        bounds = np.maximum(B(1-bounds), B(boxmap))
        cols = 1-morph.rb_closing(boxmap, (int(20 * scale), int(scale)))
        cols = morph.select_regions(cols, sl.aspect, min=self.parameter['csminaspect'])
        cols = morph.select_regions(cols, sl.dim0, min=self.parameter['csminheight']*scale, nbest=self.parameter['maxcolseps'])
        cols = morph.r_erosion(cols, (int(0.5+scale), 0))
        cols = morph.r_dilation(cols, (int(0.5+scale), 0), origin=(int(scale/2)-1, 0))
        return cols


    def compute_colseps_mconv(self, binary, scale=1.0):
        """Find column separators using a combination of morphological
        operations and convolution."""
        #  h, w = binary.shape
        smoothed = gaussian_filter(1.0 * binary, (scale, scale * 0.5))
        smoothed = uniform_filter(smoothed, (5.0 * scale, 1))
        thresh = (smoothed < np.amax(smoothed) * 0.1)
        blocks = morph.rb_closing(binary, (int(4 * scale), int(4 * scale)))
        seps = np.minimum(blocks, thresh)
        seps = morph.select_regions(seps, sl.dim0, min=self.parameter['csminheight']*scale, nbest=self.parameter['maxcolseps'])
        blocks = morph.r_dilation(blocks, (5, 5))
        seps = np.maximum(seps, 1-blocks)
        return seps


    def compute_colseps_conv(self, binary, scale=1.0):
        """Find column separators by convolution and
        thresholding."""
        #  h, w = binary.shape
        # find vertical whitespace by thresholding
        smoothed = gaussian_filter(1.0 * binary, (scale, scale * 0.5))
        smoothed = uniform_filter(smoothed, (5.0 * scale, 1))
        thresh = (smoothed < np.amax(smoothed) * 0.1)
        # find column edges by filtering
        grad = gaussian_filter(1.0 * binary, (scale, scale * 0.5), order=(0, 1))
        grad = uniform_filter(grad, (10.0 * scale, 1))
        # grad = abs(grad) # use this for finding both edges
        grad = (grad > 0.5 * np.amax(grad))
        # combine edges and whitespace
        seps = np.minimum(thresh, maximum_filter(grad, (int(scale), int(5 * scale))))
        seps = maximum_filter(seps, (int(2 * scale), 1))
        # select only the biggest column separators
        seps = morph.select_regions(seps, sl.dim0, min=self.parameter['csminheight']*scale, nbest=self.parameter['maxcolseps'])
        return seps


    def compute_colseps(self, binary, scale):
        """Computes column separators either from vertical black lines or whitespace."""
        log.debug("considering at most %g whitespace column separators" % self.parameter['maxcolseps'])
        colseps = self.compute_colseps_conv(binary, scale)
        if self.parameter['maxseps'] > 0:
            log.debug("considering at most %g black column separators" % self.parameter['maxseps'])
            # TODO BUG compute_separators_morph not ported! 
            seps = self.compute_separators_morph(binary, scale)
            #colseps = self.compute_colseps_morph(binary, scale)
            colseps = np.maximum(colseps, seps)
            binary = np.minimum(binary, 1-seps)
        return colseps, binary


    def remove_hlines(self, binary, scale, maxsize=10):
        labels, _ = morph.label(binary)
        objects = morph.find_objects(labels)
        for i, b in enumerate(objects):
            if sl.width(b) > maxsize * scale:
                labels[b][labels[b] == i + 1] = 0
        return np.array(labels != 0, 'B')


    def compute_segmentation(self, binary, scale):
        """Given a binary image, compute a complete segmentation into
        lines, computing both columns and text lines."""
        binary = np.array(binary, 'B')

        # start by removing horizontal black lines, which only
        # interfere with the rest of the page segmentation
        binary = self.remove_hlines(binary, scale)

        # do the column finding
        log.debug("computing column separators")
        colseps, binary = self.compute_colseps(binary, scale)

        # now compute the text line seeds
        log.debug("computing lines")
        bottom, top, boxmap = self.compute_gradmaps(binary, scale)
        log.debug("bottom=%s top=%s boxmap=%s", bottom, top, boxmap)
        seeds = self.compute_line_seeds(binary, bottom, top, colseps, scale)

        # spread the text line seeds to all the remaining
        # components
        log.debug("propagating labels")
        llabels = morph.propagate_labels(boxmap, seeds, conflict=0)
        log.debug("spreading labels")
        spread = morph.spread_labels(seeds, maxdist=scale)
        llabels = np.where(llabels > 0, llabels, spread * binary)
        segmentation = llabels * binary
        return segmentation

# ----- >8 ------------------------------
# End snippety snap

    def __init__(self, *args, **kwargs):
        kwargs['ocrd_tool'] = OCRD_TOOL['tools']['ocrd-ocropy-segment']
        kwargs['version'] = OCRD_TOOL['version']
        super(OcropySegment, self).__init__(*args, **kwargs)

    def process(self):
        """
        Segment with ocropy
        """

        for (n, input_file) in enumerate(self.input_files):
            log.info("INPUT FILE %i / %s", n, input_file)
            downloaded_file = self.workspace.download_file(input_file)
            log.info("downloaded_file %s", downloaded_file)
            pcgts = page_from_file(downloaded_file)
            page_width = pcgts.get_Page().get_imageWidth()
            page_height = pcgts.get_Page().get_imageHeight()
            # TODO binarized variant from get_AlternativeImage()
            image_url = pcgts.get_Page().imageFilename
            log.info("pcgts %s", pcgts)

            binary = ocrolib.read_image_binary(self.workspace.download_url(image_url))
            binary = 1 - binary

            scale = self.parameter['scale'] if self.parameter['scale'] != 0 else psegutils.estimate_scale(binary)
            log.debug(binary)

            pseg = self.compute_segmentation(binary, scale)
            log.debug("pseg=%s", pseg)

            # TODO reading order / enumber
            #  log.debug("finding reading order")
            #  lines = psegutils.compute_lines(pseg, scale)
            #  order = psegutils.reading_order([l.bounds for l in lines])
            #  lsort = psegutils.topsort(order)

            regions = ocrolib.RegionExtractor()
            regions.setPageLines(pseg)

            dummyRegion = TextRegionType(id="dummy", Coords=CoordsType(points="0,0 %s,0 %s,%s 0,%s" % (
                page_width, page_width, page_height, page_height)))
            pcgts.get_Page().add_TextRegion(dummyRegion)

            for lineno in range(1, regions.length()):
                log.debug("id=%s bbox=%s", regions.id(lineno), regions.bbox(lineno))
                textline = TextLineType(
                    id=concat_padded("line", lineno),
                    Coords=CoordsType(points=points_from_x0y0x1y1(regions.bbox(lineno)))
                )
                dummyRegion.add_TextLine(textline)
            ID = concat_padded(self.output_file_grp, n)
            self.workspace.add_file(
                ID=ID,
                file_grp=self.output_file_grp,
                mimetype=MIMETYPE_PAGE,
                local_filename="%s/%s" % (self.output_file_grp, ID),
                content=to_xml(pcgts)
            )

            #  log.debug(pseg)
            #  for l in lines:
            #      log.debug("bounds=%s label=%s", l.bounds, l.label)
            #  log.debug(order)
            #  log.debug(lsort)

            #  #  print(res)
            #  for lineno, box in enumerate(res['boxes']):
            #      textline = TextLineType(
            #          id=concat_padded("line", lineno),
            #          Coords=CoordsType(points=points_from_x0y0x1y1(box))
            #      )
            #      dummyRegion.add_TextLine(textline)
