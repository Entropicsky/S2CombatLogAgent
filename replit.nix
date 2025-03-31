{ pkgs }: {
  deps = [
    pkgs.python310
    pkgs.python310Packages.pip
    pkgs.python310Packages.setuptools
    pkgs.python310Packages.wheel
    pkgs.python310Packages.tqdm
    pkgs.python310Packages.sqlalchemy
    pkgs.python310Packages.streamlit
    pkgs.python310Packages.pandas
    pkgs.python310Packages.numpy
    pkgs.python310Packages.matplotlib
    pkgs.python310Packages.plotly
    pkgs.python310Packages.sqlparse
    pkgs.python310Packages.requests
  ];
  env = {
    PYTHONPATH = "${pkgs.python310Packages.setuptools}/lib/python3.10/site-packages:${pkgs.python310Packages.pip}/lib/python3.10/site-packages:${pkgs.python310Packages.wheel}/lib/python3.10/site-packages:$PYTHONPATH";
  };
} 