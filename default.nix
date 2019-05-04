with import <nixpkgs> {};

stdenv.mkDerivation {
  name = "impurePythonEnv";
  buildInputs = [
    # for the subshell, otherwise prompt, arrows, delete broken
    bashInteractive
    python3Full
    python3Packages.virtualenv
    python3Packages.pip
    pipenv
    git
    stdenv
    gcc
    openssl
    libffi
    docker_compose
  ];
  src = null;
  shellHook = ''
  # set SOURCE_DATE_EPOCH so that we can use python wheels
  SOURCE_DATE_EPOCH=$(date +%s)
  PIPENV_VENV_DIR=$(pipenv --venv)
  export PYTHONPATH=$PIPENV_VENV_DIR/lib/python3.6/site-packages/:$PYTHONPATH
  export PATH=$PIPENV_VENV_DIR/bin:$PATH
  '';
}
