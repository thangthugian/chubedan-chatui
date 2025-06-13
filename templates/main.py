from typing import Annotated
from fastapi import FastAPI, UploadFile, File, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import google.generativeai as genai
from PIL import Image
import io
import os

# Cấu hình Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel(model_name="gemini-1.5-flash")

chat_log = []  # Lưu lịch sử hội thoại

# FastAPI
app = FastAPI()
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def get_form(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@app.websocket("/ws")
async def chat(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Nhận nội dung người dùng gửi lên
            user_input = await websocket.receive_text()

            # Lưu vào lịch sử chat
            chat_log.append({'role': 'user', 'parts': [user_input]})

            # Gửi nội dung đến Gemini, sử dụng stream
            response = model.generate_content(
                chat_log,
                stream=True  # Quan trọng: để nhận dữ liệu theo luồng
            )

            ai_response = ""
            for chunk in response:
                if chunk.text:
                    ai_response += chunk.text
                    await websocket.send_text(chunk.text)

            # Lưu phản hồi của AI vào lịch sử chat
            chat_log.append({'role': 'model', 'parts': [ai_response]})

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        await websocket.send_text(f"Error: {str(e)}")

@app.post("/", response_class=HTMLResponse)
async def post_prompt(request: Request, user_input: Annotated[str, Form(...)]):
    # Gửi prompt đến Gemini
    response = model.generate_content(user_input)
    result = response.text

    return templates.TemplateResponse("home.html", {
        "request": request,
        "user_input": user_input,
        "response": result
    })

@app.get("/image", response_class=HTMLResponse)
async def image_form(request: Request):
    return templates.TemplateResponse("image.html", {"request": request})


@app.post("/generate-image", response_class=HTMLResponse)
async def generate_image(
    request: Request,
    user_input: Annotated[str, Form(...)],
    image: UploadFile = File(...)
):
    image_bytes = await image.read()
    img = Image.open(io.BytesIO(image_bytes))

    response = model.generate_content([user_input, img])
    result = response.text

    return templates.TemplateResponse("image.html", {
        "request": request,
        "user_input": user_input,
        "response": result
    })
