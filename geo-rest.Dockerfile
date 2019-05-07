from python:3.7

WORKDIR /code
copy Pipfile .
copy Pipfile.lock .
copy geo-rest/geo_rest geo_rest
RUN pip install pipenv
RUN pipenv install --system --deploy

EXPOSE 80

ENTRYPOINT ["gunicorn", "-b", ":80", "geo_rest.geo_rest:app"]
CMD []
