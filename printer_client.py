"""Send a rendered receipt image straight to a network ESC/POS thermal
printer -- no browser, no OS print dialog, no "print server". This is what
replaces opening the receipt HTML in Edge and clicking Print.
"""
from escpos.printer import Network


def print_receipt_image(img, ip, port=9100, timeout=8, cut_mode='FULL'):
    """Connects to the printer, streams the raster image, feeds a short
    tail and cuts. Raises on any connection/printing failure -- callers
    are expected to catch and surface the error to the operator."""
    if not ip:
        raise ValueError('No printer IP configured -- set it in Settings.')

    printer = Network(ip, port=port, timeout=timeout)
    try:
        printer.image(img, impl='bitImageRaster')
        printer.cut(mode=cut_mode)
    finally:
        printer.close()
