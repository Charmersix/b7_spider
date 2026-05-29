FROM python:3.11-slim

WORKDIR /app

COPY jjt_gallery_server.py /app/jjt_gallery_server.py
COPY jjt_gallery /app/jjt_gallery
COPY jjt_images /app/jjt_images

ENV PYTHONUNBUFFERED=1
ENV JJT_GALLERY_HOST=0.0.0.0
ENV JJT_GALLERY_PORT=6969

EXPOSE 6969

CMD ["python", "/app/jjt_gallery_server.py"]
