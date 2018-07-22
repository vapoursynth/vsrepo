VSRepo
======

A simple package repository for VapourSynth. It is implemented in a way that
keeps no state between invocations and can therefore be pointed at any
pre-existing plugin and script directory.


Usage
-----

Install plugins and scripts. The identifier, namespace/modulename and name
are searched for matches in that order.
```
vsrepo.py install havsfunc ffms2 d2v
```

Update all installed packages to the latest version.
```
vsrepo.py upgrade all
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

VSRUpdate.py has two main purposes.