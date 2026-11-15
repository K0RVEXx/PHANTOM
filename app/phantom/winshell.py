"""Windows Explorer integration: PHANTOM folder icon and desktop shortcut.

Windows does not keep folder-icon attributes when a ZIP is extracted, so PHANTOM
re-applies them on start. A .bat file cannot have its own icon, so PHANTOM can
create a desktop shortcut (with the PHANTOM icon) that starts PHANTOM.bat.
No administrator rights are needed.
"""
import base64
import os
import subprocess

from . import BASE_DIR, ROOT_DIR

SUPPORTED = os.name == "nt"
ICON_PATH = os.path.join(BASE_DIR, "assets", "phantom-folder.ico")
DESKTOP_INI = os.path.join(ROOT_DIR, "desktop.ini")
BAT_PATH = os.path.join(ROOT_DIR, "PHANTOM.bat")
SHORTCUT_NAME = "PHANTOM.lnk"

FILE_ATTRIBUTE_READONLY = 0x01
FILE_ATTRIBUTE_HIDDEN = 0x02
FILE_ATTRIBUTE_SYSTEM = 0x04
SHCNE_UPDATEDIR = 0x00001000
SHCNE_ASSOCCHANGED = 0x08000000
SHCNF_PATHW = 0x0005


def _attrs(path):
    import ctypes
    return ctypes.windll.kernel32.GetFileAttributesW(path)


def _add_attrs(path, flags):
    import ctypes
    current = _attrs(path)
    if current == -1 or current == 0xFFFFFFFF:
        return False
    if current & flags == flags:
        return True
    return bool(ctypes.windll.kernel32.SetFileAttributesW(path, current | flags))


def folder_icon_ready():
    if not (SUPPORTED and os.path.isfile(DESKTOP_INI) and os.path.isfile(ICON_PATH)):
        return False
    folder, ini = _attrs(ROOT_DIR), _attrs(DESKTOP_INI)
    return bool(folder & FILE_ATTRIBUTE_READONLY) and \
        ini & (FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM) == (FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM)


def apply_folder_icon():
    """Make Explorer show the PHANTOM icon on the PHANTOM folder.
    Returns True if it changed something."""
    if not SUPPORTED or not os.path.isfile(DESKTOP_INI) or not os.path.isfile(ICON_PATH):
        return False
    if folder_icon_ready():
        return False
    ok = _add_attrs(DESKTOP_INI, FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM)
    # The read-only flag on a folder only tells Explorer to read desktop.ini;
    # files inside stay fully writable.
    ok = _add_attrs(ROOT_DIR, FILE_ATTRIBUTE_READONLY) and ok
    if ok:
        import ctypes
        shell = ctypes.windll.shell32
        shell.SHChangeNotify(SHCNE_UPDATEDIR, SHCNF_PATHW, ctypes.c_wchar_p(ROOT_DIR), None)
        shell.SHChangeNotify(SHCNE_ASSOCCHANGED, 0, None, None)
    return ok


def desktop_dir():
    """The user's real Desktop folder (also when it is redirected to OneDrive)."""
    import ctypes
    from ctypes import wintypes
    buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
    CSIDL_DESKTOPDIRECTORY = 0x10
    if ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_DESKTOPDIRECTORY, None, 0, buf) == 0:
        return buf.value
    return os.path.join(os.path.expanduser("~"), "Desktop")


def shortcut_path():
    return os.path.join(desktop_dir(), SHORTCUT_NAME)


def shortcut_exists():
    return SUPPORTED and os.path.isfile(shortcut_path())


def _ps_quote(s):
    return "'" + s.replace("'", "''") + "'"


def create_shortcut():
    """Create a desktop shortcut with the PHANTOM icon that starts PHANTOM.bat.
    Returns the shortcut path. Raises OSError on failure."""
    if not SUPPORTED:
        raise OSError("Only available on Windows")
    lnk = shortcut_path()
    # WScript.Shell converts paths to the ANSI code page (Ø -> O on Hungarian Windows),
    # so the Unicode IShellLinkW interface is used instead.
    script = SHELL_LINK_CS + (
        "[PhantomShellLink]::Create({lnk}, {target}, {cwd}, {icon}, "
        "'PHANTOM - Proxy Rotation System')"
    ).format(lnk=_ps_quote(lnk), target=_ps_quote(BAT_PATH),
             cwd=_ps_quote(ROOT_DIR), icon=_ps_quote(ICON_PATH))
    r = _powershell(script)
    if r.returncode != 0 or not os.path.isfile(lnk):
        raise OSError((r.stderr or "shortcut was not created").strip().splitlines()[-1])
    if shortcut_target() != BAT_PATH:
        raise OSError("shortcut target was saved incorrectly")
    return lnk


def _powershell(script):
    """Run a PowerShell script. -EncodedCommand (UTF-16) keeps non-ASCII characters
    in paths (e.g. Ø, á, ő) intact, which plain -Command does not."""
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=30, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def shortcut_target():
    """Target path stored in the desktop shortcut (None if there is none)."""
    if not shortcut_exists():
        return None
    script = SHELL_LINK_CS + "[PhantomShellLink]::Target({lnk})".format(lnk=_ps_quote(shortcut_path()))
    return _powershell(script).stdout.strip() or None


# Minimal Unicode shell-link helper, compiled by PowerShell on demand.
SHELL_LINK_CS = r"""
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [Text.Encoding]::UTF8
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;
using System.Text;

[ComImport, Guid("000214F9-0000-0000-C000-000000000046"),
 InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IShellLinkW {
    void GetPath([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder f, int c, IntPtr d, uint fl);
    void GetIDList(out IntPtr p);
    void SetIDList(IntPtr p);
    void GetDescription([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder n, int c);
    void SetDescription([MarshalAs(UnmanagedType.LPWStr)] string n);
    void GetWorkingDirectory([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder d, int c);
    void SetWorkingDirectory([MarshalAs(UnmanagedType.LPWStr)] string d);
    void GetArguments([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder a, int c);
    void SetArguments([MarshalAs(UnmanagedType.LPWStr)] string a);
    void GetHotkey(out short h);
    void SetHotkey(short h);
    void GetShowCmd(out int s);
    void SetShowCmd(int s);
    void GetIconLocation([Out, MarshalAs(UnmanagedType.LPWStr)] StringBuilder p, int c, out int i);
    void SetIconLocation([MarshalAs(UnmanagedType.LPWStr)] string p, int i);
    void SetRelativePath([MarshalAs(UnmanagedType.LPWStr)] string p, uint r);
    void Resolve(IntPtr h, uint f);
    void SetPath([MarshalAs(UnmanagedType.LPWStr)] string f);
}

[ComImport, Guid("00021401-0000-0000-C000-000000000046")]
class CShellLink { }

public static class PhantomShellLink {
    public static void Create(string lnk, string target, string cwd, string icon, string desc) {
        var link = (IShellLinkW)new CShellLink();
        link.SetPath(target);
        link.SetWorkingDirectory(cwd);
        link.SetIconLocation(icon, 0);
        link.SetDescription(desc);
        ((IPersistFile)link).Save(lnk, true);
    }
    public static string Target(string lnk) {
        var link = (IShellLinkW)new CShellLink();
        ((IPersistFile)link).Load(lnk, 0);
        var sb = new StringBuilder(1024);
        link.GetPath(sb, sb.Capacity, IntPtr.Zero, 4);
        return sb.ToString();
    }
}
'@
"""


def remove_shortcut():
    if shortcut_exists():
        os.remove(shortcut_path())
        return True
    return False
