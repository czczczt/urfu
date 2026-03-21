import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
from sklearn.metrics import mean_absolute_percentage_error

# ['Make', 'Model', 'Year', 'Style', 'Fuel', 'Engine', 'Distance', 'Cylinders', 'Transmission', 'Drive', 'Wheel', 'Color', 'ID']

def clear_df(df):
    df['Engine'] = df['Engine'].astype(str).str.extract(r'(\d+\.?\d*)')[0].astype(float)
    df['Distance'] = df['Distance'].astype(str).str.extract(r'(\d+\.?\d*)')[0].astype(float)

    df['Engine'] = df['Engine'].fillna(df['Engine'].median())
    df['Cylinders'] = df['Cylinders'].fillna(df['Cylinders'].median())
    df['Fuel'] = df['Fuel'].fillna('Petrol')

    df['Wheel'] = df['Wheel'].map({'Left wheel': 1, 'Right-hand drive': 0})
    df['Transmission'] = df['Transmission'].map({'Automatic': 0, 'Manual': 1, 'Tiptronic': 2, 'Variator': 3})
    df['Drive'] = df['Drive'].map({'Front': 0, 'Rear': 1, '4x4': 2})

    if 'Price' in df.columns:
        df = df[df['Price'] >= 600]
        price_q1 = df['Price'].quantile(0.065)
        price_max = df['Price'].quantile(0.925)
        df = df[(df['Price'] >= price_q1) & (df['Price'] <= price_max)]

        df = df[df['Engine'].map(df['Engine'].value_counts()) >= 7]
        df = df[df['Cylinders'].map(df['Cylinders'].value_counts()) >= 4]
        df = df[df['Make'].map(df['Make'].value_counts()) >= 4]
        df = df[df['Year'].map(df['Year'].value_counts()) >= 3] # падает mae, растет mape
    return df


def add_features(df): # добавить колонки
    df['Age'] = 2025 - df['Year']
    df['LDistance'] = np.log1p(df['Distance'])
    df['LEngine'] = np.log1p(df['Engine'])
    df['EnginePerAge'] = df['Engine'] / (df['Age'] + 1)
    df['DistancePerYear'] = df['Distance'] / (df['Age'] + 1)
    df['Engine_sq'] = df['Engine'] ** 2
    df['Engine_Distance'] = df['Engine'] * df['Distance']
    df['Age_sq'] = df['Age'] ** 2
    return df


df = pd.read_csv('cars_train.csv')
df = clear_df(df)
for i2 in ['Make', 'Model', 'Fuel', 'Style']: # попробовать добавить цвет
    df[i2] = df[i2].astype('category').cat.codes
df = df.drop(columns=['ID', 'Color'])
df = add_features(df)

q33 = df['Price'].quantile(0.33)
q66 = df['Price'].quantile(0.66)
df1 = df[df['Price'] <= q33].copy()
df2 = df[(df['Price'] > q33) & (df['Price'] <= q66)].copy()
df3 = df[df['Price'] > q66].copy()

# model1 = RandomForestRegressor(n_estimators=210, max_depth=21, random_state=42, n_jobs=-1)
# model2 = ExtraTreesRegressor(n_estimators=145, max_depth=19, random_state=42, n_jobs=-1)
# model3 = GradientBoostingRegressor(n_estimators=315, max_depth=7, learning_rate=0.055, random_state=42)

#==============================================НИЩИЕ====================================================================
X1 = df1.drop('Price', axis=1)
y1 = df1['Price']
X1_train, X1_valid, y1_train, y1_valid = train_test_split(X1, y1, test_size=0.1, random_state=42)
model1_1 = RandomForestRegressor(n_estimators=145, max_depth=19, random_state=42, n_jobs=-1)
model1_2 = ExtraTreesRegressor(n_estimators=145, max_depth=19, random_state=42, n_jobs=-1)
model1_3 = GradientBoostingRegressor(n_estimators=315, max_depth=7, learning_rate=0.055, random_state=42)
model1_1.fit(X1_train, y1_train)
model1_2.fit(X1_train, y1_train)
model1_3.fit(X1_train, y1_train)
y1_pred = (model1_1.predict(X1_valid) * 0.2 + model1_2.predict(X1_valid) * 0.5 + model1_3.predict(X1_valid) * 0.3)
mae1 = mean_absolute_error(y1_valid, y1_pred)
mape1 = mean_absolute_percentage_error(y1_valid, y1_pred)

#==============================================СРЕДНИЕ==================================================================
X2 = df2.drop('Price', axis=1)
y2 = df2['Price']
X2_train, X2_valid, y2_train, y2_valid = train_test_split(X2, y2, test_size=0.1, random_state=42)
model2_1 = RandomForestRegressor(n_estimators=145, max_depth=19, random_state=42, n_jobs=-1)
model2_2 = ExtraTreesRegressor(n_estimators=145, max_depth=19, random_state=42, n_jobs=-1)
model2_3 = GradientBoostingRegressor(n_estimators=315, max_depth=7, learning_rate=0.055, random_state=42)
model2_1.fit(X2_train, y2_train)
model2_2.fit(X2_train, y2_train)
model2_3.fit(X2_train, y2_train)
y2_pred = (model2_1.predict(X2_valid) * 0.2 + model2_2.predict(X2_valid) * 0.5 + model2_3.predict(X2_valid) * 0.3)
mae2 = mean_absolute_error(y2_valid, y2_pred)
mape2 = mean_absolute_percentage_error(y2_valid, y2_pred)

#==============================================БУРЖУИ===================================================================
X3 = df3.drop('Price', axis=1)
y3 = df3['Price']
X3_train, X3_valid, y3_train, y3_valid = train_test_split(X3, y3, test_size=0.1, random_state=42)
model3_1 = RandomForestRegressor(n_estimators=145, max_depth=19, random_state=42, n_jobs=-1)
model3_2 = ExtraTreesRegressor(n_estimators=145, max_depth=19, random_state=42, n_jobs=-1)
model3_3 = GradientBoostingRegressor(n_estimators=315, max_depth=7, learning_rate=0.055, random_state=42)
model3_1.fit(X3_train, y3_train)
model3_2.fit(X3_train, y3_train)
model3_3.fit(X3_train, y3_train)
y3_pred = (model3_1.predict(X3_valid) * 0.2 + model3_2.predict(X3_valid) * 0.5 + model3_3.predict(X3_valid) * 0.3)
mae3 = mean_absolute_error(y3_valid, y3_pred)
mape3 = mean_absolute_percentage_error(y3_valid, y3_pred)


MAE = (mae1 * len(y1_valid) + mae2 * len(y2_valid) + mae3 * len(y3_valid)) / (len(y1_valid) + len(y2_valid) + len(y3_valid))
MAPE = (mape1 * len(y1_valid) + mape2 * len(y2_valid) + mape3 * len(y3_valid)) / (len(y1_valid) + len(y2_valid) + len(y3_valid))
print('MAE:', MAE)
print('MAPE, %:', MAPE)

df_test = pd.read_csv('cars_test.csv')
df_test = df_test.drop_duplicates(subset=['ID'], keep='first')
df_test = clear_df(df_test)
for i2 in ['Make', 'Model', 'Fuel', 'Style']:
    df_test[i2] = df_test[i2].astype('category').cat.codes
df_test = df_test.drop(columns=['Color'])
df_test = add_features(df_test)
X_test = df_test[X1.columns]

y1_pred_test = (model1_1.predict(X_test) * 0.2 + model1_2.predict(X_test) * 0.5 + model1_3.predict(X_test) * 0.3)
y2_pred_test = (model2_1.predict(X_test) * 0.2 + model2_2.predict(X_test) * 0.5 + model2_3.predict(X_test) * 0.3)
y3_pred_test = (model3_1.predict(X_test) * 0.2 + model3_2.predict(X_test) * 0.5 + model3_3.predict(X_test) * 0.3)

y_ensemble_avg = (y1_pred_test + y2_pred_test + y3_pred_test) / 3  # Среднее всех 3
y_pred_test = np.zeros(len(df_test))

for i in range(len(df_test)):
    avg_price = y_ensemble_avg[i]
    if avg_price <= q33:
        y_pred_test[i] = y1_pred_test[i]
    elif avg_price <= q66:
        y_pred_test[i] = y2_pred_test[i]
    else:
        y_pred_test[i] = y3_pred_test[i]

df_submit = df_test.loc[X_test.index, ['ID']].copy()
df_submit['Predict'] = y_pred_test
df_submit.to_csv('submit3.csv', index=False)