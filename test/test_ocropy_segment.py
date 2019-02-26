# pylint: disable=import-error

import os
import shutil
from tempfile import TemporaryDirectory

from test.base import TestCase, assets, main

from ocrd.resolver import Resolver
from ocrd_ocropy.segment import OcropySegment

PARAM_JSON = assets.url_of('param-segment.json')

WORKSPACE_DIR = '/tmp/ocrd-ocropy-segment-test'

class TestOcropySegment(TestCase):

    def setUp(self):
        if os.path.exists(WORKSPACE_DIR):
            shutil.rmtree(WORKSPACE_DIR)
        os.makedirs(WORKSPACE_DIR)

    def test_run1(self):
        resolver = Resolver()
        with TemporaryDirectory() as tempdir:
            workspace = resolver.workspace_from_url(assets.path_to('kant_aufklaerung_1784-binarized/data/mets.xml'), dst_dir=tempdir)
            proc = OcropySegment(
                workspace,
                input_file_grp="OCR-D-IMG-BIN",
                output_file_grp="OCR-D-SEG-OCROPY-TEST",
                page_id='P_0017',
            )
            #  print(proc.parameter)
            proc.process()
            workspace.save_mets()

if __name__ == "__main__":
    main()
