#%Module

#=====
# Created by singularity-hpc (https://github.com/singularityhub/singularity-hpc)
# ##
# quay.io/biocontainers/ldsc:1.0.1--pyhdfd78af_2 on 2023-08-15 12:08:41.851818
#=====

proc ModulesHelp { } {

    puts stderr "This module is a singularity container wrapper for quay.io/biocontainers/ldsc:1.0.1--pyhdfd78af_2 v1.0.1--pyhdfd78af_2"
    
    puts stderr ""
    puts stderr "Container (available through variable SINGULARITY_CONTAINER):"
    puts stderr ""
    puts stderr " - /software/hgi/containers/shpc/quay.io/biocontainers/ldsc/1.0.1--pyhdfd78af_2/quay.io-biocontainers-ldsc-1.0.1--pyhdfd78af_2-sha256:308ddebaa643d50306779ce42752eb4c4a3e1635be74531594013959e312af2c.sif"
    puts stderr ""
    puts stderr "Commands include:"
    puts stderr ""
    puts stderr " - ldsc-run:"
    puts stderr "       singularity run -B <moduleDir>/99-shpc.sh:/.singularity.d/env/99-shpc.sh <container> \"\$@\""
    puts stderr " - ldsc-shell:"
    puts stderr "       singularity shell -s /bin/sh -B <moduleDir>/99-shpc.sh:/.singularity.d/env/99-shpc.sh <container>"
    puts stderr " - ldsc-exec:"
    puts stderr "       singularity exec -B <moduleDir>/99-shpc.sh:/.singularity.d/env/99-shpc.sh <container> \"\$@\""
    puts stderr " - ldsc-inspect-runscript:"
    puts stderr "       singularity inspect -r <container>"
    puts stderr " - ldsc-inspect-deffile:"
    puts stderr "       singularity inspect -d <container>"
    puts stderr " - ldsc-container:"
    puts stderr "       echo \"\$SINGULARITY_CONTAINER\""
    puts stderr ""
    puts stderr " - ldsc.py:"
    puts stderr "       singularity exec -B <moduleDir>/99-shpc.sh:/.singularity.d/env/99-shpc.sh <container> /usr/local/bin/ldsc.py \"\$@\""
    puts stderr " - munge_sumstats.py:"
    puts stderr "       singularity exec -B <moduleDir>/99-shpc.sh:/.singularity.d/env/99-shpc.sh <container> /usr/local/bin/munge_sumstats.py \"\$@\""
    puts stderr " - f2py2:"
    puts stderr "       singularity exec -B <moduleDir>/99-shpc.sh:/.singularity.d/env/99-shpc.sh <container> /usr/local/bin/f2py2 \"\$@\""
    puts stderr " - f2py2.7:"
    puts stderr "       singularity exec -B <moduleDir>/99-shpc.sh:/.singularity.d/env/99-shpc.sh <container> /usr/local/bin/f2py2.7 \"\$@\""
    puts stderr " - shiftBed:"
    puts stderr "       singularity exec -B <moduleDir>/99-shpc.sh:/.singularity.d/env/99-shpc.sh <container> /usr/local/bin/shiftBed \"\$@\""
    puts stderr " - annotateBed:"
    puts stderr "       singularity exec -B <moduleDir>/99-shpc.sh:/.singularity.d/env/99-shpc.sh <container> /usr/local/bin/annotateBed \"\$@\""
    puts stderr " - bamToBed:"
    puts stderr "       singularity exec -B <moduleDir>/99-shpc.sh:/.singularity.d/env/99-shpc.sh <container> /usr/local/bin/bamToBed \"\$@\""
    puts stderr " - bamToFastq:"
    puts stderr "       singularity exec -B <moduleDir>/99-shpc.sh:/.singularity.d/env/99-shpc.sh <container> /usr/local/bin/bamToFastq \"\$@\""
    puts stderr " - bed12ToBed6:"
    puts stderr "       singularity exec -B <moduleDir>/99-shpc.sh:/.singularity.d/env/99-shpc.sh <container> /usr/local/bin/bed12ToBed6 \"\$@\""
    puts stderr " - bedToBam:"
    puts stderr "       singularity exec -B <moduleDir>/99-shpc.sh:/.singularity.d/env/99-shpc.sh <container> /usr/local/bin/bedToBam \"\$@\""
    puts stderr " - bedToIgv:"
    puts stderr "       singularity exec -B <moduleDir>/99-shpc.sh:/.singularity.d/env/99-shpc.sh <container> /usr/local/bin/bedToIgv \"\$@\""
    puts stderr " - bedpeToBam:"
    puts stderr "       singularity exec -B <moduleDir>/99-shpc.sh:/.singularity.d/env/99-shpc.sh <container> /usr/local/bin/bedpeToBam \"\$@\""

    puts stderr ""
    puts stderr "For each of the above, you can export:"
    puts stderr ""
    puts stderr " - SINGULARITY_OPTS: to define custom options for singularity (e.g., --debug)"
    puts stderr " - SINGULARITY_COMMAND_OPTS: to define custom options for the command (e.g., -b)"
    puts stderr " - SINGULARITY_CONTAINER: The Singularity (sif) path"

}

set view_dir "[file dirname [file dirname ${ModulesCurrentModulefile}] ]"
set view_name "[file tail ${view_dir}]"
set view_module ".view_module"
set view_modulefile "${view_dir}/${view_module}"

if {[file exists ${view_modulefile}]} {
    source ${view_modulefile}
}

# Environment - only set if not already defined
if { ![info exists ::env(SINGULARITY_OPTS)] } {
    setenv SINGULARITY_OPTS ""
}
if { ![info exists ::env(SINGULARITY_COMMAND_OPTS)] } {
    setenv SINGULARITY_COMMAND_OPTS ""
}

# Variables

set name        quay.io/biocontainers/ldsc:1.0.1--pyhdfd78af_2
set version     1.0.1--pyhdfd78af_2
set description "$name - $version"
set containerPath /software/hgi/containers/shpc/quay.io/biocontainers/ldsc/1.0.1--pyhdfd78af_2/quay.io-biocontainers-ldsc-1.0.1--pyhdfd78af_2-sha256:308ddebaa643d50306779ce42752eb4c4a3e1635be74531594013959e312af2c.sif


set helpcommand "This module is a singularity container wrapper for quay.io/biocontainers/ldsc:1.0.1--pyhdfd78af_2 v1.0.1--pyhdfd78af_2. "
set busybox "BusyBox v1.32.1 (2021-04-13 11:15:36 UTC) multi-call binary."
set deb-list "gcc-8-base_8.3.0-6_amd64.deb, libc6_2.28-10_amd64.deb, libgcc1_1%3a8.3.0-6_amd64.deb, bash_5.0-4_amd64.deb, libc-bin_2.28-10_amd64.deb, libtinfo6_6.1+20181013-2+deb10u2_amd64.deb, ncurses-base_6.1+20181013-2+deb10u2_all.deb, base-files_10.3+deb10u9_amd64.deb"
set glibc "GNU C Library (Debian GLIBC 2.28-10) stable release version 2.28."
set io.buildah.version "1.19.6"
set org.label-schema.build-arch "amd64"
set org.label-schema.build-date "Tuesday_15_August_2023_12:8:5_BST"
set org.label-schema.schema-version "1.0"
set org.label-schema.usage.singularity.deffile.bootstrap "docker"
set org.label-schema.usage.singularity.deffile.from "quay.io/biocontainers/ldsc@sha256:308ddebaa643d50306779ce42752eb4c4a3e1635be74531594013959e312af2c"
set org.label-schema.usage.singularity.version "3.10.0"
set pkg-list "gcc-8-base, libc6, libgcc1, bash, libc-bin, libtinfo6, ncurses-base, base-files"


# directory containing this modulefile, once symlinks resolved (dynamically defined)
set moduleDir   [file dirname [expr { [string equal [file type ${ModulesCurrentModulefile}] "link"] ? [file readlink ${ModulesCurrentModulefile}] : ${ModulesCurrentModulefile} }]]

# conflict with modules with the same alias name
conflict ldsc
conflict quay.io/biocontainers/ldsc:1.0.1--pyhdfd78af_2
conflict ldsc.py
conflict munge_sumstats.py
conflict f2py2
conflict f2py2.7
conflict shiftBed
conflict annotateBed
conflict bamToBed
conflict bamToFastq
conflict bed12ToBed6
conflict bedToBam
conflict bedToIgv
conflict bedpeToBam


# singularity environment variable to set shell
setenv SINGULARITY_SHELL /bin/sh

# service environment variable to access full SIF image path
setenv SINGULARITY_CONTAINER "${containerPath}"

# interactive shell to any container, plus exec for aliases
set shellCmd "singularity \${SINGULARITY_OPTS} shell \${SINGULARITY_COMMAND_OPTS} -s /bin/sh -B ${moduleDir}/99-shpc.sh:/.singularity.d/env/99-shpc.sh  ${containerPath}"
set execCmd "singularity \${SINGULARITY_OPTS} exec \${SINGULARITY_COMMAND_OPTS} -B ${moduleDir}/99-shpc.sh:/.singularity.d/env/99-shpc.sh  "
set runCmd "singularity \${SINGULARITY_OPTS} run \${SINGULARITY_COMMAND_OPTS} -B ${moduleDir}/99-shpc.sh:/.singularity.d/env/99-shpc.sh  ${containerPath}"
set inspectCmd "singularity \${SINGULARITY_OPTS} inspect \${SINGULARITY_COMMAND_OPTS} "

# if we have any wrapper scripts, add bin to path
prepend-path PATH "${moduleDir}/bin"

# "aliases" to module commands
if { [ module-info shell bash ] } {
  if { [ module-info mode load ] } {
 
 
 
 
 
 
 
 
 
 
 
 

  }
  if { [ module-info mode remove ] } {
 
 
 
 
 
 
 
 
 
 
 
 

  }
} else {













}



#=====
# Module options
#=====
module-whatis "    Name: quay.io/biocontainers/ldsc:1.0.1--pyhdfd78af_2"
module-whatis "    Version: 1.0.1--pyhdfd78af_2"


module-whatis "    busybox: BusyBox v1.32.1 (2021-04-13 11:15:36 UTC) multi-call binary."
module-whatis "    deb-list: gcc-8-base_8.3.0-6_amd64.deb, libc6_2.28-10_amd64.deb, libgcc1_1%3a8.3.0-6_amd64.deb, bash_5.0-4_amd64.deb, libc-bin_2.28-10_amd64.deb, libtinfo6_6.1+20181013-2+deb10u2_amd64.deb, ncurses-base_6.1+20181013-2+deb10u2_all.deb, base-files_10.3+deb10u9_amd64.deb"
module-whatis "    glibc: GNU C Library (Debian GLIBC 2.28-10) stable release version 2.28."
module-whatis "    io.buildah.version: 1.19.6"
module-whatis "    org.label-schema.build-arch: amd64"
module-whatis "    org.label-schema.build-date: Tuesday_15_August_2023_12:8:5_BST"
module-whatis "    org.label-schema.schema-version: 1.0"
module-whatis "    org.label-schema.usage.singularity.deffile.bootstrap: docker"
module-whatis "    org.label-schema.usage.singularity.deffile.from: quay.io/biocontainers/ldsc@sha256:308ddebaa643d50306779ce42752eb4c4a3e1635be74531594013959e312af2c"
module-whatis "    org.label-schema.usage.singularity.version: 3.10.0"
module-whatis "    pkg-list: gcc-8-base, libc6, libgcc1, bash, libc-bin, libtinfo6, ncurses-base, base-files"

module load /software/modules/ISG/singularity/3.10.0