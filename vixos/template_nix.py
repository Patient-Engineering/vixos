import os


def generate_local_nix() -> str:
    return """{
  # services.xserver.xkbOptions = "ctrl:nocaps";
  # services.xserver.layout = "pl(intl)";
}"""


def generate_nix(package: str, executable: str, pubkey: str) -> str:
    return """{pkgs, ...}:
let
  application = "${pkgs.%s}/bin/%s";
  appRunner = pkgs.writeShellScriptBin "app" ''
    ARGS_FILE=/home/user/.args
    ARGS=$(cat $ARGS_FILE)
    rm $ARGS_FILE

    ${application} $ARGS
    systemctl poweroff
  '';
in {
  imports = [
    <nixpkgs/nixos/modules/virtualisation/qemu-vm.nix>
    <base.nix>
    <local.nix>
  ];

  # TODO: this is currently hilariously insecure, VMs can login to others.
  users.extraUsers.user = {
      openssh.authorizedKeys.keys = [
        "%s"
      ];
  };
  users.users.root = {
      openssh.authorizedKeys.keys = [
        "%s"
      ];
  };

  environment.systemPackages = [ appRunner pkgs.%s ];

  services.xserver.displayManager.sessionCommands = "${appRunner}/bin/app &";

  networking.hostName = "%s";
}
""" % (
        package,
        executable,
        pubkey,
        pubkey,
        package,
        package,
    )


def generate_base_nix():
    uid = os.getuid()
    return base_nix % (uid)


base_nix = """{pkgs, ...}:
{
  systemd.services.home-user-build-xmonad = {
    description = "Link xmonad configuration";
    serviceConfig = {
      ExecStart = "/bin/sh -c 'mkdir -p /home/user/.xmonad && ln -sf /etc/xmonad.hs /home/user/.xmonad/xmonad.hs && /run/current-system/sw/bin/xmonad --recompile'";
      RemainAfterExit = "yes";
      User = "user";
      Restart = "on-failure";
      TimeoutSec = 10;
    };
    wantedBy = [ "multi-user.target" ];
  };

  services.xserver = {
    enable = true;
    desktopManager.xterm.enable = false;
    displayManager = {
      lightdm.enable = true;
      autoLogin = {
        enable = true;
        user = "user";
      };
    };
    windowManager.xmonad.enable = true;
  };

  services.spice-vdagentd.enable = true;

  # enable sshd on every guest.
  services.openssh = {
    enable = true;
    passwordAuthentication = false;
    kbdInteractiveAuthentication = false;
  };

  # TODO: this is temporary, for development and debugging.
  users.users.root = { initialPassword = "root"; };
  users.extraUsers.user = {
    uid = %s;
    isNormalUser = true;
    extraGroups = [ "audio" ];
    createHome = true;
    initialPassword = "user";
  };

  environment.etc."xmonad.hs".text = ''
import XMonad
main = xmonad def
  { workspaces = [ "" ]
  , borderWidth = 0
  , startupHook = startup
  }

startup :: X ()
startup = do
  spawn "while [ 1 ]; do ${pkgs.spice-vdagent}/bin/spice-vdagent -x; done &"
  '';

  systemd.services.mount-home-user = {
    description = "Mount /home/user (crutch)";
    serviceConfig = {
      ExecStart = "/bin/sh -c '/run/current-system/sw/bin/mount -t 9p -o trans=virtio,version=9p2000.L home /home/user'";
      RemainAfterExit = "yes";
      Type = "oneshot";
      User = "root";
    };
    wantedBy = [ "sysinit.target" ];
  };

  services.getty.autologinUser = "user";

  systemd.services."serial-getty@ttyS0" = {
    enable = true;
    wantedBy = [ "getty.target" ];
    serviceConfig.Restart = "always";
  };

  systemd.user.services."xrandr" = {
    serviceConfig = {
      StartLimitBurst = 100;
    };
    script = "${pkgs.xorg.xrandr}/bin/xrandr --output Virtual-1 --mode $(${pkgs.xorg.xrandr}/bin/xrandr | grep '   ' | head -n 2 | tail -n 1 | ${pkgs.gawk}/bin/awk '{ print $1 }')";
  };

  systemd.user.timers."xrandr" = {
    description = "Auto update resolution crutch";
    timerConfig = {
      OnBootSec = "1s";
      OnUnitInactiveSec = "1s";
      Unit = "xrandr.service";
      AccuracySec = "1us";
    };
    wantedBy = ["timers.target"];
  };
}"""
