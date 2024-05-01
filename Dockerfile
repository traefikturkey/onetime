# syntax=docker/dockerfile:1.4
ARG PYTHON_VERSION=3.12

FROM python:${PYTHON_VERSION}-slim-bookworm as base
LABEL maintainer="Mike Glenn <mglenn@ilude.com>"

ARG PUID=${PUID:-1000}
ARG PGID=${PGID:-1000}

ARG USER=anvil
ARG TZ=America/New_York
ENV USER=${USER}
ENV TZ=${TZ}

ARG PROJECT_NAME
ENV PROJECT_NAME=${PROJECT_NAME}

ARG PROJECT_PATH=/app
ENV PROJECT_PATH=${PROJECT_PATH}

ENV PYTHON_DEPS_PATH=/dependencies
ENV PYTHONPATH="${PYTHONPATH}:${PYTHON_DEPS_PATH}"
ENV PYTHONUNBUFFERED=TRUE

ENV LANGUAGE=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV DEBIAN_FRONTEND=noninteractive
ENV DEBCONF_NONINTERACTIVE_SEEN=true

ENV HOME=/home/${USER}
ARG TERM_SHELL=zsh
ENV TERM_SHELL=${TERM_SHELL} 

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    bash-completion \
    ca-certificates \
    curl \
    gosu \
    less \
    libopenblas-dev \
    locales \
    make \
    sudo \
    tzdata \
    zsh && \
    # locales
    echo "$(LANGUAGE)" > /etc/locale.gen && \
    locale-gen en_US.UTF-8 && \
    # cleanup
    apt-get autoremove -fy && \
    apt-get clean && \
    apt-get autoclean -y && \
    rm -rf /var/lib/apt/lists/* 

RUN sed -i 's/UID_MAX .*/UID_MAX    100000/' /etc/login.defs && \
    groupadd --gid ${PGID} ${USER} && \
    useradd --uid ${PUID} --gid ${PGID} -s /bin/${TERM_SHELL} -m ${USER} && \
    echo "alias l='ls -lhA --color=auto --group-directories-first'" >> /etc/zshenv && \
    echo "alias es='env | sort'" >> /etc/zshenv && \
    echo "PS1='\h:\$(pwd) \$ '" >> /etc/zshenv && \
    mkdir -p ${PROJECT_PATH} && \
    chown -R ${USER}:${USER} ${PROJECT_PATH} && \
    # https://www.jeffgeerling.com/blog/2023/how-solve-error-externally-managed-environment-when-installing-pip3
    rm -rf /usr/lib/python${PYTHON_VERSION}/EXTERNALLY-MANAGED 

COPY --chmod=755 <<-"EOF" /usr/local/bin/docker-entrypoint.sh
#!/bin/bash
set -e
if [ -v DOCKER_ENTRYPOINT_DEBUG ] && [ "$DOCKER_ENTRYPOINT_DEBUG" == 1 ]; then
  set -x
  set -o xtrace
fi

if [ "$(id -u)" = "0" ]; then
  groupmod -o -g ${PGID:-1000} ${USER}
  usermod -o -u ${PUID:-1000} ${USER}

  # get gid of docker socket file
  SOCK_DOCKER_GID=`stat -c %g /var/run/docker.sock`
  groupmod -o -g "$SOCK_DOCKER_GID" ${USER}

  # Add call to gosu to drop from root user to jenkins user
  # when running original entrypoint
  set -- gosu ${USER} "$@"
fi

echo "Running: $@"
exec $@
EOF

WORKDIR $PROJECT_PATH
ENTRYPOINT [ "/usr/local/bin/docker-entrypoint.sh" ]


##############################
# Begin build 
##############################
FROM base as build

RUN apt-get update && apt-get install -y --no-install-recommends \
    binutils \
    build-essential \
    pkg-config gfortran \
    cmake \
    coreutils \
    extra-cmake-modules \
    findutils \
    git \
    openssl \
    openssh-client \
    sqlite3 \
    libsqlite3-dev \
    wget && \
    apt-get autoremove -fy && \
    apt-get clean && \
    apt-get autoclean -y && \
    rm -rf /var/lib/apt/lists/* 

COPY requirements.txt requirements.txt
RUN pip3 install --upgrade pip && \
    pip3 install --upgrade setuptools && \
    pip3 install --upgrade wheel && \
    mkdir -p ${PYTHON_DEPS_PATH} && \
    chown -R ${USER}:${USER} ${PROJECT_PATH} ${PYTHON_DEPS_PATH} && \
    pip3 install --no-cache-dir --target=${PYTHON_DEPS_PATH} -r requirements.txt && \
    rm -rf requirements.txt

##############################
# Begin production 
##############################
FROM base as production

COPY --from=build --chown=${USER}:${USER}	${PYTHON_DEPS_PATH} ${PYTHON_DEPS_PATH}
COPY --chown=${USER}:${USER} app ${PROJECT_PATH}

ENV FLASK_ENV=production

RUN mkdir /cache && \
    chown -R ${USER}:${USER} /cache

CMD [ "python3", "app.py" ]

##############################
# Begin devcontainer 
##############################
FROM build as devcontainer

RUN apt-get update && apt-get install -y --no-install-recommends \
    graphviz \
    imagemagick \
    libffi-dev \
    libjpeg-dev \
    libpng-dev \
    libpq-dev \
    libssl-dev \
    libxml2-dev \
    libxslt-dev \
    gnuplot \
    gnuplot-x11 \
    libzmq3-dev && \
    apt-get autoremove -fy && \
    apt-get clean && \
    apt-get autoclean -y && \
    rm -rf /var/lib/apt/lists/*

    RUN pip3 install --no-cache-dir --target=${PYTHON_DEPS_PATH} docutils h5py ipykernel ipython jupyter jupyterhub notebook numpy nltk pyyaml pylint scikit-learn scipy==1.11.0 watermark
    RUN pip3 install --no-cache-dir --target=${PYTHON_DEPS_PATH} --no-deps --prefer-binary matplotlib seaborn plotly graphviz imutils keras
    RUN pip3 install --no-cache-dir --target=${PYTHON_DEPS_PATH} --prefer-binary pandas-datareader bottleneck scipy duckdb sqlalchemy pyautogui requests_cache statsmodels
    #RUN pip3 install --no-cache-dir --target=${PYTHON_DEPS_PATH} gensim torch tensorflow


RUN apt-get update && apt-get install -y --no-install-recommends \
    ansible \
    dnsutils \
    exa \
    iproute2 \
    jq \
    openssh-client \
    ripgrep \
    rsync \
    sshpass \
    sudo \
    tar \
    tree \
    util-linux \
    yq \
    zsh-autosuggestions \
    zsh-syntax-highlighting && \
    apt-get autoremove -fy && \
    apt-get clean && \
    apt-get autoclean -y && \
    rm -rf /var/lib/apt/lists/* 



RUN echo ${USER} ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/${USER} && \
    chmod 0440 /etc/sudoers.d/${USER} && \
    chown ${USER} /var/run/docker.sock

USER ${USER}

COPY --chown=${USER}:${USER} .devcontainer/ansible ${PROJECT_PATH}/.devcontainer/ansible
RUN LC_ALL=C.UTF-8 ansible-playbook --inventory 127.0.0.1 --connection=local .devcontainer/ansible/requirements.yml && \
    LC_ALL=C.UTF-8 ansible-playbook --inventory 127.0.0.1 --connection=local .devcontainer/ansible/setup-docker.yml
  
# https://code.visualstudio.com/remote/advancedcontainers/start-processes#_adding-startup-commands-to-the-docker-image-instead
CMD [ "sleep", "infinity" ]
