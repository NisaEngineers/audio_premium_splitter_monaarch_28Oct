import os
import shutil
import uuid
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from audio_separator.separator import Separator
from pyngrok import ngrok

app = FastAPI(title="Audio Separation API")
os.makedirs("user_data", exist_ok=True)
# Mount static folder for serving separated files
app.mount("/static", StaticFiles(directory="user_data"), name="static")

# Load model once globally
separator = Separator()
separator.load_model("htdemucs_6s.yaml")

def get_rename_mapping(base_name: str):
    return {
        f"{base_name}_(Bass)_htdemucs_6s.wav": "bass.wav",
        f"{base_name}_(Piano)_htdemucs_6s.wav": "piano.wav",
        f"{base_name}_(Other)_htdemucs_6s.wav": "strings_or_pads.wav",
        f"{base_name}_(Vocals)_htdemucs_6s.wav": "vocals.wav",
        f"{base_name}_(Guitar)_htdemucs_6s.wav": "guitar.wav",
        f"{base_name}_(Drums)_htdemucs_6s.wav": "drums.wav",
    }

@app.post("/separate/")
async def separate_audio(file: UploadFile = File(...)):
    user_id = str(uuid.uuid4())
    user_folder = os.path.join("user_data", user_id)
    os.makedirs(user_folder, exist_ok=True)

    input_path = os.path.join(user_folder, file.filename)
    with open(input_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    output_files = separator.separate(input_path)

    base_name, _ = os.path.splitext(file.filename)
    rename_mapping = get_rename_mapping(base_name)

    renamed_files = []
    for old_path in output_files:
        old_name = os.path.basename(old_path)
        if old_name in rename_mapping:
            new_path = os.path.join(user_folder, rename_mapping[old_name])
            os.rename(old_path, new_path)
            renamed_files.append(new_path)

    file_urls = [
        f"/static/{user_id}/{os.path.basename(f)}" for f in renamed_files
    ]

    return {"user_id": user_id, "files": file_urls}

@app.get("/download/{user_id}/{filename}")
async def download_file(user_id: str, filename: str):
    file_path = os.path.join("user_data", user_id, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, filename=filename)
    return {"error": "File not found"}

if __name__ == "__main__":
    import uvicorn
    from pyngrok import ngrok

    # 🔑 Set your ngrok token here
    NGROK_TOKEN = "30eW25DS9DAjbcnfLl0dgJGLi26_3cRvbDMAmAjCXVeyi6pmt"
    ngrok.set_auth_token(NGROK_TOKEN)

    # Start a tunnel on port 8000
    public_url = ngrok.connect(8000)
    print(f"Public URL: {public_url}")

    # Run FastAPI app asynchronously in the existing event loop
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    await server.serve()
