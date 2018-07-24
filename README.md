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