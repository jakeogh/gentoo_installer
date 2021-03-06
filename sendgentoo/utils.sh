#!/bin/bash
#set -o nounset

emerge_world()
{
    echo "emerge_world()" > /dev/stderr
    emerge -pv     --backtrack=130 --usepkg=n --tree -u --ask n -n world > /dev/stderr
    emerge -pv -F    --backtrack=130 --usepkg=n --tree -u --ask n -n world > /dev/stderr
    emerge --quiet --backtrack=130 --usepkg=n --tree -u --ask n -n world > /dev/stderr || exit 1
}


add_accept_keyword() {
    pkg="${1}"
    shift
    line="=${pkg} **"
    grep -E "^=${pkg} \*\*$" /etc/portage/package.accept_keywords && return 0
    echo "${line}" >> /etc/portage/package.accept_keywords
}


install_pkg_force_compile()
{
    set +u
    . /etc/profile
    set -u
    echo -e "\ninstall_pkg_force_compile() got args: $@" > /dev/stderr
    emerge --with-bdeps=y -pv     --tree --usepkg=n -u --ask n -n $@ > /dev/stderr
    echo -e "\ninstall_pkg_force_compile() got args: $@" > /dev/stderr
    emerge --with-bdeps=y --quiet --tree --usepkg=n -u --ask n -n $@ > /dev/stderr || exit 1
}


install_pkg()
{
    set +u
    . /etc/profile
    set -u
    echo -e "\ninstall_pkg() got args: $@" > /dev/stderr
    emerge --with-bdeps=y -pv     --tree --usepkg=n    -u --ask n -n $@ > /dev/stderr
    echo -e "\ninstall_pkg() got args: $@" > /dev/stderr
    emerge --with-bdeps=y --quiet --tree --usepkg=n    -u --ask n -n $@ > /dev/stderr
}

install_pkg_force()
{
    set +u
    . /etc/profile
    set -u
    echo -e "\ninstall_pkg_force() got args: $@" > /dev/stderr
    CONFIG_PROTECT="-*" emerge --with-bdeps=y -pv     --tree --usepkg=n -u --ask n --autounmask --autounmask-write  -n $@ > /dev/stderr
    echo -e "\ninstall_pkg_force() got args: $@" > /dev/stderr
    CONFIG_PROTECT="-*" emerge --with-bdeps=y --quiet --tree --usepkg=n -u --ask n --autounmask --autounmask-write  -n $@ > /dev/stderr
    CONFIG_PROTECT="-*" emerge --with-bdeps=y --quiet --tree --usepkg=n -u --ask n --autounmask --autounmask-write  -n $@ > /dev/stderr
}


#add_accept_keyword "dev-python/kcl-9999"
#add_accept_keyword "dev-python/sendgentoo-9999"
#add_accept_keyword "dev-python/sqlalchemy-utils-9999"
#add_accept_keyword "dev-python/python-getdents-9999"
#add_accept_keyword "dev-python/fastentrypoints-9999"
#add_accept_keyword "dev-python/untokenize-9999"
#add_accept_keyword "dev-python/ic-9999"

