from tensorflow.keras.models import load_model
from decouple import config

def get_model():
    model_path = config("MODEL_PATH", default="stock_prediction_model.keras")
    try:
        return load_model(model_path)
    except Exception as e:
        raise Exception(f"Model loading failed: {str(e)}")
