FROM python:3.13-slim

WORKDIR /app

RUN pip install --upgrade pip \
 && pip install uv

#Copy only metadata to leverage layer caching
COPY pyproject.toml README.md ./

# bring in package code
COPY src ./src

#build & install packages
RUN pip install .

#bring in the rest of the code
COPY . .

#Expose the MCP server port
EXPOSE 3000

#console-script entrypoint
CMD ["unifi-network-mcp"]