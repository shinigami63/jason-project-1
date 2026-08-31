"""Send a rendered receipt image straight to the thermal printer -- no
browser, no OS print dialog, no "print server". This is what replaces
opening the receipt HTML in Edge and clicking Print.

Two connection modes are supported:
  - 'windows_name': the printer is installed in Windows under a name (e.g.
    "kitchen", as shown in Devices & Printers) and raw ESC/POS bytes are
    pushed straight through the Windows print spooler via pywin32,
    bypassing whatever driver is attached to it -- this works regardless
    of which "graphical" driver Windows has for the printer, since the
    printer itself still speaks ESC/POS on the wire and the spooler just
    hands the raw bytes through. This is the default, since it's the
    common setup for a receipt printer that shows up as a normal Windows
    printer rather than a bare network socket.
  - 'network_ip': the printer is addressed directly over the network by
    IP:port (the usual raw ESC/POS port is 9100), with no Windows printer
    object involved at all.
"""


def _connect(mode, printer_name, ip, port, timeout):
    if mode == 'windows_name':
        if not printer_name:
            raise ValueError('No Windows printer name configured -- set it in Settings.')
        from escpos.printer import Win32Raw
        return Win32Raw(printer_name)
    if not ip:
        raise ValueError('No printer IP configured -- set it in Settings.')
    from escpos.printer import Network
    return Network(ip, port=port, timeout=timeout)


def print_receipt_image(img, mode='windows_name', printer_name='', ip='', port=9100, timeout=8, cut_mode='FULL'):
    """Connects to the printer, streams the raster image, feeds a short
    tail and cuts. Raises on any connection/printing failure -- callers
    are expected to catch and surface the error to the operator."""
    printer = _connect(mode, printer_name, ip, port, timeout)
    try:
        printer.image(img, impl='bitImageRaster')
        printer.cut(mode=cut_mode)
    finally:
        printer.close()
