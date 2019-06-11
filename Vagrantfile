
# Inspired by https://github.com/borgbackup/borg/blob/master/Vagrantfile

$cpus = Integer(ENV.fetch('VMCPUS', '4'))  # create VMs with that many cpus
$xdistn = Integer(ENV.fetch('XDISTN', '4'))  # dispatch tests to that many pytest workers
$wmem = $xdistn * 256  # give the VM additional memory for workers [MB]

def fs_init(user)
  return <<-EOF
    # clean up (wrong/outdated) stuff we likely got via rsync:
    rm -rf /vagrant/vorta/.tox 2> /dev/null
    find /vagrant/vorta/src -name '__pycache__' -exec rm -rf {} \\; 2> /dev/null
    chown -R #{user} /vagrant/vorta
    touch ~#{user}/.bash_profile ; chown #{user} ~#{user}/.bash_profile
    echo 'export LANG=en_US.UTF-8' >> ~#{user}/.bash_profile
    echo 'export LC_CTYPE=en_US.UTF-8' >> ~#{user}/.bash_profile
    echo 'export XDISTN=#{$xdistn}' >> ~#{user}/.bash_profile
  EOF
end

def packages_debianoid(user)
  return <<-EOF
    apt update
    # install all the (security and other) updates
    apt dist-upgrade -y
    # for building borgbackup and dependencies:
    apt install -y libssl-dev libacl1-dev liblz4-dev libfuse-dev fuse pkg-config
    usermod -a -G fuse #{user}
    chgrp fuse /dev/fuse
    chmod 666 /dev/fuse
    apt install -y fakeroot build-essential git curl
    apt install -y python3-dev python3-setuptools python-virtualenv python3-virtualenv
    # for building python:
    apt install -y zlib1g-dev libbz2-dev libncurses5-dev libreadline-dev liblzma-dev libsqlite3-dev libffi-dev
    # minimal window manager and system tray icon support
    apt install xvfb herbstluftwm gnome-keyring
  EOF
end

def install_pyenv(boxname)
  return <<-EOF
    curl -s -L https://raw.githubusercontent.com/yyuu/pyenv-installer/master/bin/pyenv-installer | bash
    echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> ~/.bash_profile
    echo 'eval "$(pyenv init -)"' >> ~/.bash_profile
    echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bash_profile
    echo 'export PYTHON_CONFIGURE_OPTS="--enable-shared"' >> ~/.bash_profile
  EOF
end

def install_pythons(boxname)
  return <<-EOF
    . ~/.bash_profile
    pyenv install 3.6.8
    pyenv rehash
  EOF
end

def build_pyenv_venv(boxname)
  return <<-EOF
    . ~/.bash_profile
    cd /vagrant/vorta
    pyenv global 3.6.8
    pyenv virtualenv 3.6.8 vorta-env
    ln -s ~/.pyenv/versions/vorta-env .
  EOF
end

def install_pyinstaller()
  return <<-EOF
    . ~/.bash_profile
    cd /vagrant/vorta
    . vorta-env/bin/activate
    pip install pyinstaller
  EOF
end

def build_binary_with_pyinstaller(boxname)
  return <<-EOF
    . ~/.bash_profile
    cd /vagrant/vorta
    . vorta-env/bin/activate
    pip uninstall pyqt5
    # Use older PyQt5 to avoid DBus issue.
    pip install pyqt5==5.11.3
    pyinstaller --clean --noconfirm vorta.spec
  EOF
end

def run_tests(boxname)
  return <<-EOF
    . ~/.bash_profile
    cd /vagrant/vorta
    . vorta-env/bin/activate
    tox
    fi
  EOF
end

def darwin_prepare()
  return <<-EOF
    /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
    brew install python
    echo 'export PATH="/usr/local/opt/qt/bin/:$PATH"' >> ~/.bash_profile
    cd /vagrant
    pip3 install -e .
    pip3 install -r requirements.d/dev.txt
    brew bundle --file=requirements.d/Brewfile
  EOF
end

def darwin_build()
  return <<-EOF
    cd /vagrant
    make Vorta.app
  EOF
end

Vagrant.configure(2) do |config|

   config.vm.define "jessie64" do |b|
     b.vm.box = "debian/jessie64"
     b.vm.provider :virtualbox do |v|
       v.memory = 1024 + $wmem
     end
     b.vm.provision "fs init", :type => :shell, :inline => fs_init("vagrant")
     b.vm.provision "packages debianoid", :type => :shell, :inline => packages_debianoid("vagrant")
     b.vm.provision "install pyenv", :type => :shell, :privileged => false, :inline => install_pyenv("jessie64")
     b.vm.provision "install pythons", :type => :shell, :privileged => false, :inline => install_pythons("jessie64")
     b.vm.provision "build env", :type => :shell, :privileged => false, :inline => build_pyenv_venv("jessie64")
     b.vm.provision "install pyinstaller", :type => :shell, :privileged => false, :inline => install_pyinstaller()
     b.vm.provision "build binary with pyinstaller", :type => :shell, :privileged => false, :inline => build_binary_with_pyinstaller("jessie64")
#     b.vm.provision "run tests", :type => :shell, :privileged => false, :inline => run_tests("jessie64")
   end

    config.vm.define "darwin64" do |b|
        b.vm.box = "monsenso/macos-10.13"
        b.vm.provider :virtualbox do |v|
          v.memory = 1536 + $wmem
          v.customize ['modifyvm', :id, '--ostype', 'MacOS_64']
          v.customize ['modifyvm', :id, '--paravirtprovider', 'default']
          v.customize ["setextradata", :id, "VBoxInternal/CPUM/SSE4.1", "1"]
          v.customize ["setextradata", :id, "VBoxInternal/CPUM/SSE4.2", "1"]
          # Adjust CPU settings according to
          # https://github.com/geerlingguy/macos-virtualbox-vm
#          v.customize ['modifyvm', :id, '--cpuidset',
#                       '00000001', '000306a9', '00020800', '80000201', '178bfbff']
          # Disable USB variant requiring Virtualbox proprietary extension pack
          v.customize ["modifyvm", :id, '--usbehci', 'off', '--usbxhci', 'off']
        end

        b.vm.synced_folder ".", "/vagrant", type: "rsync", user: "vagrant", group: "staff"
        b.vm.provision "darwin_prepare", :type => :shell, :privileged => false, :inline => darwin_prepare()
        b.vm.provision "darwin_build", :type => :shell, :privileged => false, run: "always", :inline => darwin_build()
    end

   config.vm.define "win64" do |b|
     b.vm.box = "gusztavvargadr/windows-10"
     b.vm.provider :virtualbox do |v|
       v.memory = 1024 + $wmem
     end
   end

  # config.vm.define "freebsd64" do |b|
  #   b.vm.box = "freebsd12-amd64"
  #   b.vm.provider :virtualbox do |v|
  #     v.memory = 1024 + $wmem
  #   end
  #   b.ssh.shell = "sh"
  #   b.vm.provision "fs init", :type => :shell, :inline => fs_init("vagrant")
  #   b.vm.provision "packages freebsd", :type => :shell, :inline => packages_freebsd
  #   b.vm.provision "build env", :type => :shell, :privileged => false, :inline => build_sys_venv("freebsd64")
  #   b.vm.provision "install borg", :type => :shell, :privileged => false, :inline => install_borg(true)
  #   b.vm.provision "install pyinstaller", :type => :shell, :privileged => false, :inline => install_pyinstaller()
  #   b.vm.provision "build binary with pyinstaller", :type => :shell, :privileged => false, :inline => build_binary_with_pyinstaller("freebsd64")
  #   b.vm.provision "run tests", :type => :shell, :privileged => false, :inline => run_tests("freebsd64")
  # end

  # TODO: create more VMs with python 3.6 and openssl 1.1.
  # See branch 1.1-maint for a better equipped Vagrantfile (but still on py34 and openssl 1.0).
end
