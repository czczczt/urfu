from pathlib import Path
from transformers import pipeline
from PIL import Image
import pandas as pd
from tqdm import tqdm
import os

IMAGE_FOLDER_TRAIN = "train"
IMAGE_FOLDER_TEST = "test"
OUTPUT_CSV = "submit1.csv"

df_train = pd.read_csv(os.path.join(IMAGE_FOLDER_TRAIN, 'labels.csv'))


def make_zs_prompts(df):
    return df['class'].unique()


prompts4clf = make_zs_prompts(df_train)

classifier = pipeline(
    "zero-shot-image-classification",
    model="openai/clip-vit-base-patch32",
    device=0
)


def classify_images(image_folder, classifier, candidate_labels):
    results = []
    image_paths = [
        p for p in Path(image_folder).iterdir()
        if p.suffix.lower() in {'.jpg', '.jpeg', '.png'}
    ]
    for img_path in tqdm(image_paths, desc="Classifying"):
        image = Image.open(img_path).convert("RGB")
        preds = classifier(image, candidate_labels=candidate_labels)
        top_pred = preds[0]["label"]
        results.append({"ID": img_path.name, "predicted_class": top_pred})

    return pd.DataFrame(results)


results_df = classify_images(
    image_folder=IMAGE_FOLDER_TRAIN,
    classifier=classifier,
    candidate_labels=prompts4clf
)

merged_df = pd.merge(df_train, results_df, on='ID', how='outer')
merged_df['is_correct'] = merged_df.apply(lambda row: row['class'] in row['predicted_class'], axis=1)
accuracy = merged_df['is_correct'].mean()
print(f"Accuracy на train: {accuracy}")

results_df = classify_images(
    image_folder=IMAGE_FOLDER_TEST,
    classifier=classifier,
    candidate_labels=prompts4clf
)

results_df.to_csv(OUTPUT_CSV, index=False)   