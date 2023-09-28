from flask import Flask, render_template, request,jsonify
from pyexiftool import exiftool
from utility import exiftool_exe
import os
import tempfile
import cv2 as cv
import datetime
from subprocess import run, PIPE,check_output
from werkzeug.utils import secure_filename
app = Flask(__name__)

@app.route('/')
def upload_form():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return 'No file part'

    image = request.files['image']

    if image.filename == '':
        return 'No selected file'
    print(image,image.filename)
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    if '.' in image.filename and image.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS:
        pass
    else:
        return "WRONG FORMAT, Select 'png', 'jpg', 'jpeg', 'gif'"
    if image:
        # Generate a unique filename
        filename = secure_filename(image.filename)
        # Save the file to a specific folder (e.g., 'uploads')
        upload_folder = 'uploads'
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        namefile =f"uploaded.{image.filename.rsplit('.', 1)[1].lower()}"
        filepath = os.path.join(upload_folder,namefile )
        image.save(filepath)

        img = cv.imread(filepath)

        cv.imwrite(f"static/uploaded.jpg",img)
        # You can process the image here or do whatever you need with the filepath.
        # For demonstration, let's just return a success message.
        print('Image uploaded successfully and saved as {}'.format(filename))


    #1 thumbnail
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
        temp_name = temp_file.name
        output = check_output([exiftool_exe(), "-b", "-ThumbnailImage", filepath])
        temp_file.write(output)
    thumb = cv.imread(temp_name, cv.IMREAD_COLOR)
    image1 = cv.imread(filepath,cv.IMREAD_COLOR)

    if thumb is None:
        thumberror= "Thumbnail image not found!"
        thumbnail_path = None
        difference_path = None
        #return render_template('thumb.html', thumberror=thumberror)
    else:
        thumberror=None
        resized = cv.resize(thumb, image1.shape[:-1][::-1], interpolation=cv.INTER_LANCZOS4)
        diff = cv.absdiff(image1, resized)
        thumbnail_path = f"static/thumbnail.jpg"
        difference_path = f"static/difference.jpg"
        cv.imwrite(thumbnail_path, resized)
        cv.imwrite(difference_path, diff)
        #return render_template('thumb.html', thumb=thumbnail_path, diff=difference_path)


    #2 header structure
    temp_dir = tempfile.TemporaryDirectory()
    temp_file = os.path.join(temp_dir.name, "structure.html")
    p = run([exiftool_exe(), "-q","-htmldump0", filepath], stdout=PIPE)
    with open(temp_file, "w") as file:
        file.write(p.stdout.decode("utf-8"))
    with open(temp_file, "r") as file:
        html_content = file.read()

    #return html_content

    #3 EXIF
    try:
        data = {}
        last = None
        with exiftool.ExifTool(exiftool_exe()) as et:
            metadata = et.get_metadata(filepath)


            for tag, value in metadata.items():
                ignore = [
                    "SourceFile",
                    "ExifTool:ExifTool",
                    "File:FileName",
                    "File:Directory",
                    "File:FileSize",
                    "File:FileModifyDate",
                    "File:FileInodeChangeDate",
                    "File:FileAccessDate",
                    "File:FileType",
                    "File:FilePermissions",
                    "File:FileTypeExtension",
                    "File:MIMEType",
                ]
                if not value or any(t in tag for t in ignore):
                    continue
                value = str(value).replace(", use -b option to extract", "")
                value = value.replace("Binary data ", "Binary data: ")
                group, desc = tag.split(":")


                if group in data:
                    data[group].append([desc,value])
                else:
                    data[group] = [[desc,value]]






        #return render_template('exif.html', exif_data=table)

        #4 geolocation
        with exiftool.ExifTool(exiftool_exe()) as et:
            try:
                metadata = et.get_metadata(filepath)
                lat = metadata["Composite:GPSLatitude"]
                lon = metadata["Composite:GPSLongitude"]
                # Generate Google Maps URL based on latitude and longitude
                maps_url = f"https://www.google.com/maps/place/{lat},{lon}/@{lat},{lon},17z/data=!4m5!3m4!1s0x0:0x0!8m2!3d{lat}!4d{lon}"
                geoerror=None
                google_maps_url = "Geolocation OPEN in new tab"
            except KeyError:
                geoerror = 'Geolocation data not found in EXIF'
                google_maps_url=None
                maps_url=None



        #return render_template('location.html', google_maps_url=google_maps_url)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # You can process the image here (e.g., save it, analyze it, etc.)
    # For demonstration, let's just return a success message.


    # Get the current date and time
    current_datetime = datetime.datetime.now()

    # Format the date and time
    formatted_datetime = current_datetime.strftime("%b. %d, %Y, %I:%M %p")



    return render_template('metadata.html', google_maps_url=google_maps_url,exif_data=data,thumb=thumbnail_path, diff=difference_path,
                           generated_html_content=html_content,geoerror=geoerror,thumberror=thumberror,maps_url=maps_url,date=formatted_datetime)

if __name__ == '__main__':
    app.run(debug=True)
