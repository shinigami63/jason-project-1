# Getting the Kebbet Zamen app (.exe)

The Windows app you double-click is **built automatically by GitHub Actions**
(`.github/workflows/build.yml`) every time changes land on the `master`
branch. The app bundles `ui.html` and `extract.py` *inside* the `.exe`.

> **Important:** changing the source or merging a pull request does **not**
> update the `.exe` already on your computer. Each merge produces a **new**
> `.exe` — you have to download that new one and use it in place of the old.

## Download the latest app

After the workflow finishes (a minute or two after a merge), get the newest
`.exe` from the permanent release link:

**https://github.com/shinigami63/jason-project-1/releases/latest/download/KebzetZamen.exe**

Then:

1. Close the Kebbet Zamen app if it is running.
2. Replace your old `.exe` (or the file your shortcut points at) with the
   downloaded one.
3. Start it again and re-send the order from the browser extension.

### Alternative: download from the Actions run

If you prefer, open the **Actions** tab, click the most recent **"Build
Windows EXE"** run, and download the **`KebzetZamen-Windows`** artifact at the
bottom of the page (it's a `.zip` containing the `.exe`).

## What was fixed

Customer comments on Toters orders (lines that begin with the `message`
icon, e.g. `messageفرمة ناعمة`) are now picked up and printed as their own
note line under the item, kept verbatim with no translation. This only shows
up once you are running a freshly built `.exe`.
