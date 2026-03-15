import pandas as pd

df = pd.read_csv('C:/Users/pearl r/Desktop/Coffee_Sorter/Coffee_Sorter/coffee_training_data_20251127_182237.csv')

df = df.rename(columns={
    'Red'    : 'red',
    'Green'  : 'green',
    'Blue'   : 'blue',
    'Weight' : 'weight_g',
    'Quality': 'label'
})

df.insert(0, 'bean_id', ['bean_{:04d}'.format(i) for i in range(1, len(df)+1)])

df['label'] = df['label'].str.lower().str.strip()

print(df.columns.tolist())
print(df.shape)
print(df['label'].value_counts())

df.to_csv('data/sensor_readings/sensor_data.csv', index=False)
print('Saved successfully!')
