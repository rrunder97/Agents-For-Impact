FROM alpine:3.19

RUN apk add --no-cache curl ca-certificates bash

ENV VERSION=1.15.0
RUN curl -L -o /usr/local/bin/toolbox https://storage.googleapis.com/mcp-toolbox-for-databases/v${VERSION}/linux/amd64/toolbox \
    && chmod +x /usr/local/bin/toolbox

WORKDIR /app
COPY tools.yaml /app/tools.yaml

ENV PORT=5000
EXPOSE 5000

CMD ["toolbox", "--config", "/app/tools.yaml", "--port", "5000"]
