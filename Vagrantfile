
# Inspired by https://github.com/borgbackup/borg/blob/master/Vagrantfile

$cpus = Integer(ENV.fetch('VMCPUS', '4'))  # create VMs with that many cpus
$xdistn = Integer(ENV.fetch('XDISTN', '4'))  # dispatch tests to that many pytest workers
$wmem = $xdistn * 256  # give the VM additional memory for workers [MB]

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
    apt install gdm3 gnome-shell-extension-appindicator
  EOF
end


Vagrant.configure(2) do |config|
  # use rsync to copy content to the folder
  config.vm.synced_folder ".", "/vagrant/vorta", :type => "rsync", :rsync__args => ["--verbose", "--archive", "--delete", "-z"], :rsync__chown => false
  # do not let the VM access . on the host machine via the default shared folder!
  config.vm.synced_folder ".", "/vagrant", disabled: true

  config.vm.define "bionic64" do |b|
    b.vm.box = "ubuntu/bionic64"
    b.vm.provider :virtualbox do |v|
      v.memory = 1024 + $wmem
    end
    # b.vm.provision "fs init", :type => :shell, :inline => fs_init("vagrant")
    # b.vm.provision "packages debianoid", :type => :shell, :inline => packages_debianoid("vagrant")
    # b.vm.provision "build env", :type => :shell, :privileged => false, :inline => build_sys_venv("bionic64")
    # b.vm.provision "install borg", :type => :shell, :privileged => false, :inline => install_borg(true)
    # b.vm.provision "run tests", :type => :shell, :privileged => false, :inline => run_tests("bionic64")
  end

  # config.vm.define "stretch64" do |b|
  #   b.vm.box = "debian/stretch64"
  #   b.vm.provider :virtualbox do |v|
  #     v.memory = 1024 + $wmem
  #   end
  #   b.vm.provision "fs init", :type => :shell, :inline => fs_init("vagrant")
  #   b.vm.provision "packages debianoid", :type => :shell, :inline => packages_debianoid("vagrant")
  #   b.vm.provision "install pyenv", :type => :shell, :privileged => false, :inline => install_pyenv("stretch64")
  #   b.vm.provision "install pythons", :type => :shell, :privileged => false, :inline => install_pythons("stretch64")
  #   b.vm.provision "build env", :type => :shell, :privileged => false, :inline => build_pyenv_venv("stretch64")
  #   b.vm.provision "install borg", :type => :shell, :privileged => false, :inline => install_borg(true)
  #   b.vm.provision "install pyinstaller", :type => :shell, :privileged => false, :inline => install_pyinstaller()
  #   b.vm.provision "build binary with pyinstaller", :type => :shell, :privileged => false, :inline => build_binary_with_pyinstaller("stretch64")
  #   b.vm.provision "run tests", :type => :shell, :privileged => false, :inline => run_tests("stretch64")
  # end

  # config.vm.define "arch64" do |b|
  #   b.vm.box = "terrywang/archlinux"
  #   b.vm.provider :virtualbox do |v|
  #     v.memory = 1024 + $wmem
  #   end
  #   b.vm.provision "fs init", :type => :shell, :inline => fs_init("vagrant")
  #   b.vm.provision "packages arch", :type => :shell, :privileged => true, :inline => packages_arch
  #   b.vm.provision "build env", :type => :shell, :privileged => false, :inline => build_sys_venv("arch64")
  #   b.vm.provision "install borg", :type => :shell, :privileged => false, :inline => install_borg(true)
  #   b.vm.provision "run tests", :type => :shell, :privileged => false, :inline => run_tests("arch64")
  # end

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

  config.vm.define "darwin64" do |b|
    b.vm.box = "ashiq/osx-10.14"
    b.vm.provider :virtualbox do |v|
      v.memory = 1536 + $wmem
      v.customize ['modifyvm', :id, '--ostype', 'MacOS_64']
      v.customize ['modifyvm', :id, '--paravirtprovider', 'default']
      # Adjust CPU settings according to
      # https://github.com/geerlingguy/macos-virtualbox-vm
      v.customize ['modifyvm', :id, '--cpuidset',
                   '00000001', '000306a9', '00020800', '80000201', '178bfbff']
      # Disable USB variant requiring Virtualbox proprietary extension pack
      v.customize ["modifyvm", :id, '--usbehci', 'off', '--usbxhci', 'off']
    end
    # b.vm.provision "fs init", :type => :shell, :inline => fs_init("vagrant")
    # b.vm.provision "packages darwin", :type => :shell, :privileged => false, :inline => packages_darwin
    # b.vm.provision "install pyenv", :type => :shell, :privileged => false, :inline => install_pyenv("darwin64")
    # b.vm.provision "fix pyenv", :type => :shell, :privileged => false, :inline => fix_pyenv_darwin("darwin64")
    # b.vm.provision "install pythons", :type => :shell, :privileged => false, :inline => install_pythons("darwin64")
    # b.vm.provision "build env", :type => :shell, :privileged => false, :inline => build_pyenv_venv("darwin64")
    # b.vm.provision "install borg", :type => :shell, :privileged => false, :inline => install_borg(true)
    # b.vm.provision "install pyinstaller", :type => :shell, :privileged => false, :inline => install_pyinstaller()
    # b.vm.provision "build binary with pyinstaller", :type => :shell, :privileged => false, :inline => build_binary_with_pyinstaller("darwin64")
    # b.vm.provision "run tests", :type => :shell, :privileged => false, :inline => run_tests("darwin64")
  end

  # TODO: create more VMs with python 3.6 and openssl 1.1.
  # See branch 1.1-maint for a better equipped Vagrantfile (but still on py34 and openssl 1.0).
end
