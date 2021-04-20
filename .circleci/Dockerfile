FROM ubuntu:20.04

ENV DEBIAN_FRONTEND="noninteractive" TZ="Etc/UTC"

RUN apt-get update \
    && apt-get install -y python3 python3-venv libxi6 libxrender1 libxkbcommon-x11-0 \
        libdbus-1-3 libfontconfig1 libglib2.0-0 libxcb-icccm4 libxcb-image0 \
        libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
        libxcb-xinerama0 libxcb-util1 xvfb \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --uid=3434 --user-group --create-home tester
USER tester
WORKDIR /home/tester
