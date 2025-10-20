FROM opensearchproject/opensearch:2.11.0

COPY opensearch.yml /usr/share/opensearch/config/opensearch.yml

ENV OPENSEARCH_JAVA_OPTS="-Xms512m -Xmx512m"

EXPOSE 9200 9600
