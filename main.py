import cv2
import face_recognition
import numpy as np
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import io
from PIL import Image
from typing import Optional
import pyodbc
from db import get_db, FaceEncoding

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def process_image(file: UploadFile) -> np.ndarray:
    # Read image file
    contents = await file.read()
    image = Image.open(io.BytesIO(contents))

    # Convert to numpy array and RGB
    image_array = np.array(image)
    if len(image_array.shape) == 3 and image_array.shape[2] == 3:
        rgb_image = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
    else:
        raise HTTPException(status_code=400, detail="Invalid image format")

    # Detect faces and get encodings
    face_locations = face_recognition.face_locations(rgb_image)
    face_encodings = face_recognition.face_encodings(rgb_image, face_locations)

    if len(face_encodings) == 0:
        raise HTTPException(status_code=400, detail="No faces detected in the image")
    if len(face_encodings) > 1:
        raise HTTPException(
            status_code=400,
            detail="Multiple faces detected. Please provide an image with a single face",
        )

    return face_encodings[0]


@app.post("/register/{face_id}")
async def register_face(
    face_id: str, file: UploadFile = File(...), db: pyodbc.Connection = Depends(get_db)
):
    # Check if ID already exists
    cursor = db.cursor()
    cursor.execute("SELECT id FROM face_encodings WHERE id = ?", (face_id,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Face ID already exists")

    # Process the image and get face encoding
    face_encoding = await process_image(file)

    # Create FaceEncoding instance and set the encoding
    face = FaceEncoding(id=face_id)
    face.encoding = face_encoding

    # Save to database
    cursor.execute(
        "INSERT INTO face_encodings (id, encoding) VALUES (?, ?)",
        (face.id, face._encoding),
    )
    db.commit()

    return {"message": "Face registered successfully", "id": face_id}


@app.post("/identify/")
async def identify_face(
    file: UploadFile = File(...), db: pyodbc.Connection = Depends(get_db)
):
    # Process the uploaded image
    face_encoding = await process_image(file)

    # Get all face encodings from database
    cursor = db.cursor()
    cursor.execute("SELECT id, encoding FROM face_encodings")
    stored_faces = cursor.fetchall()

    if not stored_faces:
        raise HTTPException(
            status_code=404, detail="No faces registered in the database"
        )

    # Compare with stored faces
    for stored_face_row in stored_faces:
        face = FaceEncoding(id=stored_face_row[0], encoding=stored_face_row[1])
        stored_encoding = face.encoding
        # Compare faces with tolerance (default is 0.6)
        match = face_recognition.compare_faces(
            [stored_encoding], face_encoding, tolerance=0.6
        )[0]
        if match:
            return {"id": face.id}

    raise HTTPException(status_code=404, detail="No matching face found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
