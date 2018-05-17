import click

from ocrd.decorators import ocrd_cli_options, ocrd_cli_wrap_processor

from ocrd_ocropy.segment import OcropySegment

@click.command()
@ocrd_cli_options
def ocrd_ocropy_segment(*args, **kwargs):
    return ocrd_cli_wrap_processor(OcropySegment, *args, **kwargs)
