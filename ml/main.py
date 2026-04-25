from ml.preprocessing import preprocess
from ml.detection import detect


def run_pipeline(file_path: str):
    preprocessing_signal = preprocess(file_path)
    detection_signal = detect(preprocessing_signal.metadata["frames"])
    return preprocessing_signal, detection_signal


print("ML Service loaded")