VSRepo
======

A simple package repository for VapourSynth. It is implemented in a way that
keeps no state between invocations and can therefore be pointed at any
pre-existing plugin and script directory.

All packages are by default installed to the per user plugin autoload directory
and the per user Python site-packages directory. If you're using a portable
install of VapourSynth simply use the `-p` switch.

By default binaries matching the platform Python is running on are installed.
This can be overridden by adding `-t win32` or `-t win64` to the commandline.

Usage
-----

Install plugins and scripts. Identifier, namespace, modulename and name
are searched for matches in that order.
```
vsrepo.py install havsfunc ffms2 d2v
```

Update all installed packages to the latest version.
```
vsrepo.py upgrade-all
```

Fetch latest package definitions.
```
vsrepo.py update
```

List all currently installed packages.
```
vsrepo.py installed
```

List all known packages. Useful if you can't remember the namespace or
identifier.
```
vsrepo.py available
```

Remove all files related to a package. Dependencies are not taken into
consideration so uninstalling plugins may break scripts.
```
vsrepo.py uninstall nnedi3
```
# Fork This Repository

To contribute to the project, make a fork using the instructions below

---
## Step 1: Fork the Repository

1) At the top-right of the repository page, click the **Fork** button.

2) Select your GitHub account or an organization to fork the repository to. This will create a copy of the repository in your account.

---

## Step 2: Clone Your Fork

Once you’ve forked the repository, you can clone it to your local machine for development.

1. Navigate to your forked repository on GitHub (e.g., `https://github.com/your-username/vsrepo`).
2. Click the green **Code** button and copy the repository’s URL. You can choose HTTPS, SSH, or GitHub CLI.

   ![Clone button](https://docs.github.com/assets/images/help/repository/code-button.png)

3. Open your terminal and run the following command to clone the repository:

   ```bash
   git clone https://github.com/your-username/vsrepo.git

## Step 3: contribute to the project!

VSRUpdate
---------

VSRUpdate.py has two main purposes. The `compile` command which combines all
the individual package files into one distributable file and `update-local`
which queries the github api and tries to automatically add all new releases.

It's only useful if you want to update or add new packages.

Usage example:
```
vsrupdate.py update-local -o -g <github token>
vsrupdate.py compile
```