FROM public.ecr.aws/lambda/python:3.12

RUN mkdir -p /var/task/{bin,lib}
RUN dnf install -y git zip gzip tar

WORKDIR /var/task

# Collect git and necessary libs
RUN cp /usr/bin/git /var/task/bin && \
    cp /usr/libexec/git-core/git-remote-http /var/task/bin && \
    ln -s /var/task/bin/git-remote-http /var/task/bin/git-remote-https && \
    ldd /usr/bin/git | awk 'NF == 4 { system("cp " $3 " /var/task/lib/") }' && \
    ldd /usr/libexec/git-core/git-remote-http | awk 'NF == 4 { system("cp " $3 " /var/task/lib/") }'

# Collect Gitleaks
ARG GITLEAKS_VERSION="8.18.4"
ARG TARGET_ARCH="x64"
RUN curl -sLO "https://github.com/gitleaks/gitleaks/releases/download/v$GITLEAKS_VERSION/gitleaks_${GITLEAKS_VERSION}_linux_${TARGET_ARCH}.tar.gz" && \
    tar -xzOf ./gitleaks_*.tar.gz gitleaks > /var/task/bin/gitleaks && \
    chmod +x /var/task/bin/gitleaks && \
    rm -rf ./gitleaks_*.tar.gz

# Install Python libraries
COPY requirements.txt /
RUN pip3 install --no-cache -r /requirements.txt -t /var/task

COPY src/*.py /var/task

ENTRYPOINT [ "bash", "-c" ]
