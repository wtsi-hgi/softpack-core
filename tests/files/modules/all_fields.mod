#%Module

proc ModulesHelp { } {

    puts stderr "Help text line 1"
    
    puts stderr ""
    puts stderr "Help text line 2"

}

module-whatis "Name:   name_of_container  "
module-whatis   "Version:1.0.1"

module-whatis "Foo: bar"

module-whatis "Packages: pkg1, pkg2,pkg3 pkg4 "