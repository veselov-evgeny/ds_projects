import re
import pandas as pd
from os import listdir
from os.path import isfile, join
from datetime import datetime
from dateutil.relativedelta import relativedelta

import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

path = 'files'
csv_file_name = '_data.csv'

DIVISION_CODE_COL = 'Код отдела'
SERIAL_NUMBER_COL = 'Серийный номер'
WARRANTY_COL = 'Гарантия'
WARRANTY_DATE_COL = 'Дата гарантии'
PRODUCTION_DATE_COL = 'Дата выпуска'
PRODUCTION_YEAR_COL = 'Год выпуска'
COMMISSIONING_YEAR_COL = 'Год ввода в эксплуатацию'
FLOOR_COL = 'Этаж'
ROOM_COL = 'Комната'

DIVISION_CODE_SHEET_NAME = 'Оборудование в отделах'
ENV1_SHEET_NAME = 'Данные оборудования 1'
ENV2_SHEET_NAME = 'Данные оборудования 2'


def df_leading_zeros(df, columns, code_size):
    # в датафрейме df дополняет строку в столбцах columns лидирующими нулями до размера code_size
    format_string = '{0:0>' + str(code_size) + '}'
    df = df.copy()
    if type(columns) is list:
        for col in columns:
            df[col] = df[col].apply(lambda x: format_string.format(x))
    else:
        df[columns] = df[columns].apply(lambda x: format_string.format(x))
    return df


def df_show(df):
    # отображает датафрейм
    df = df.copy()
    print(df.head(5))
    return df


def df_get_column_index(df, column_text):
    # в датафрейме df в первых строках ищет назание столбца column_text и возвращает его индекс
    max_iter_count = 1000
    idx = None
    count = 0
    for _, row in df.iterrows():
        count += 1
        for row_index, value in row.items():
            if type(value) == str and value.find(column_text) >= 0:
                return row_index
            if count > max_iter_count:
                break

    return None


def df_convert_to_date(df, date_column, format):
    # в датафрейме df в столбце date_column преобразует значения в даты в формате format, либо игнорирует при ошибке
    df = df.copy()
    df[date_column] = pd.to_datetime(df[date_column], format=format, errors='ignore')
    return df


def df_copy_column(df, column_name, new_column_name):
    # в датафрейме df в копирует столбец column_name в столбец new_column_name
    df = df.copy()
    df[new_column_name] = df[column_name]
    return df


def df_fix_year(df, columns):
    # в датафрейме df в столбцах columns находит 4-х значные числа и заменяет ими значения
    year_reg = re.compile('\d{4,4}')
    df = df.copy()

    if type(columns) is not list:
        columns = [columns]

    for col in columns:
        df[col] = df[col].apply(lambda x: next((item for item in year_reg.findall(x) if item is not None), None))

    return df


def row_fix_warranty(row):
    # в строке row фиксит значение гарантии из смешанных данных в столбцах 'Гарантия' и 'Дата выпуска'
    # берёт дату из поля 'Гарантия', либо формирует, добавляя число лет или месяцев к 'Дата выпуска'
    reg = re.compile('([^-0-9.: ]+)|(\.0$)')
    warranty = reg.sub("", str(row[WARRANTY_COL]))
    production = reg.sub("", str(row[PRODUCTION_DATE_COL]))

    warranty_date = None
    warranty_int = None

    production_date = None
    production_int = None

    try:
        warranty_date = datetime.strptime(warranty, "%Y-%m-%d %H:%M:%S")
    except ValueError:
       pass

    try:
        production_date = datetime.strptime(production, "%Y-%m-%d %H:%M:%S")
    except ValueError:
       pass

    try:
        warranty_int = int(warranty)
    except ValueError:
       pass

    try:
        production_int = int(production)
    except ValueError:
       pass

    if warranty_date is not None:
        return warranty_date

    if warranty_int is not None and production_date is not None:
        if warranty_int < 6:
            warranty = production_date + relativedelta(years=warranty_int)
        elif warranty_int >= 6 and warranty_int < 100:
            warranty = production_date + relativedelta(months=warranty_int)
        elif warranty_int > 2050:
            warranty = None

    return warranty


def df_fix_warranty(df, column):
    # в строке row фиксит значение гарантии из смешанных данных в столбцах 'Гарантия' и 'Дата выпуска'
    df = df.copy()

    if len(df) > 0:
        df[column] = df.apply(row_fix_warranty, axis=1)

    return df


def df_to_int(df, columns):
    df = df.copy()
    for column in columns:
        df[column] = df[column].astype(str).replace(regex='\.0$', value='')
    return df


check_column_names = []
data = None
cnt = 0
files = [f for f in listdir(path) if isfile(join(path, f)) and f.endswith('.xlsx')]

start_time = datetime.now()

for file in files:
    cnt += 1
    file_path = join(path, file)


    print()
    print('-' * 80)
    print('cnt: {} of {}'.format(cnt, len(files)))
    print('file:', file)

    second_from_start = (datetime.now() - start_time).seconds
    print('remains (minutes): {:.1f}'.format((len(files) * second_from_start / cnt - second_from_start) / 60))


    df = pd.read_excel(file_path, None)

    if DIVISION_CODE_SHEET_NAME not in df.keys():
        print('!' * 80)
        print('Not found sheet', DIVISION_CODE_SHEET_NAME)
        break

    if ENV1_SHEET_NAME not in df.keys():
        print('!' * 80)
        print('Not found sheet', ENV1_SHEET_NAME)
        break

    if ENV2_SHEET_NAME not in df.keys():
        print('!' * 80)
        print('Not found sheet', ENV2_SHEET_NAME)
        break

    df_codes = df[DIVISION_CODE_SHEET_NAME]
    df_env_1 = df[ENV1_SHEET_NAME]
    df_env_2 = df[ENV2_SHEET_NAME]

    code_column_index = df_get_column_index(df_codes, DIVISION_CODE_COL)
    serial_column_index = df_get_column_index(df_codes, SERIAL_NUMBER_COL)

    if code_column_index is None:
        print('!' * 80)
        print('In the sheet "{}" not found column "{}"'.format(DIVISION_CODE_SHEET_NAME, DIVISION_CODE_COL))
        break

    if serial_column_index is None:
        print('!' * 80)
        print('In the sheet "{}" not found column "{}"'.format(DIVISION_CODE_SHEET_NAME, SERIAL_NUMBER_COL))
        break

    if SERIAL_NUMBER_COL not in df_env_1.columns:
        print('!' * 80)
        print('In the sheet "{}" not found column "{}"'.format(ENV1_SHEET_NAME, SERIAL_NUMBER_COL))
        break

    if SERIAL_NUMBER_COL not in df_env_2.columns:
        print('!' * 80)
        print('In the sheet "{}" not found column "{}"'.format(ENV2_SHEET_NAME, SERIAL_NUMBER_COL))
        break

    df_codes = (
        df_codes[[code_column_index, serial_column_index]]
        # drop any rows with null values
        .dropna(subset=[code_column_index])
        .reset_index(drop=True)
        # delete top row with header names
        .drop([0])
        # put leading zeros to column with codes
        .pipe(df_leading_zeros, [code_column_index], 5)
        .rename(columns={code_column_index: DIVISION_CODE_COL,
                         serial_column_index: SERIAL_NUMBER_COL})
        .astype({DIVISION_CODE_COL: 'object', SERIAL_NUMBER_COL: 'object'})
        .sort_values(by=DIVISION_CODE_COL)
    )

    default_code = df_codes[DIVISION_CODE_COL].head(1).values[0]
    print('default_code:', default_code)

    df_env_1 = (
        df_env_1.rename(str.strip, axis='columns')
        .dropna(how='all')
        .astype(str)
        .apply(lambda x: x.str.strip())
        .assign(**{"Дата выпуска": lambda x: x[PRODUCTION_YEAR_COL]})
        .pipe(df_to_int, [PRODUCTION_DATE_COL])
        .pipe(df_fix_year, [PRODUCTION_YEAR_COL, COMMISSIONING_YEAR_COL])
        .pipe(df_convert_to_date, PRODUCTION_DATE_COL, '%Y-%m-%d')
        .pipe(df_convert_to_date, WARRANTY_COL, '%Y-%m-%d')
        .pipe(df_fix_warranty, WARRANTY_DATE_COL)
        .pipe(df_to_int, [FLOOR_COL, ROOM_COL])
        .merge(df_codes, on=SERIAL_NUMBER_COL, how='left')
        .fillna(value={DIVISION_CODE_COL: default_code})
    )

    df_env_2 = (
        df_env_2.rename(str.strip, axis='columns')
        # .replace('(\s|\n)+', None, regex=True)
        .dropna(how='all')
        .astype(str)
        .apply(lambda x: x.str.strip())
        .assign(**{"Дата выпуска": lambda x: x[PRODUCTION_YEAR_COL]})
        .pipe(df_to_int, [PRODUCTION_DATE_COL])
        .pipe(df_fix_year, [PRODUCTION_YEAR_COL, COMMISSIONING_YEAR_COL])
        .pipe(df_convert_to_date, PRODUCTION_DATE_COL, '%Y-%m-%d')
        .pipe(df_convert_to_date, WARRANTY_COL, '%Y-%m-%d')
        .pipe(df_fix_warranty, WARRANTY_DATE_COL)
        .pipe(df_to_int, [FLOOR_COL, ROOM_COL])
        .merge(df_codes, on=SERIAL_NUMBER_COL, how='left')
        .fillna(value={DIVISION_CODE_COL: default_code})
    )

    print('len(df_codes): {} ({})'.format(len(df_codes), len(df_codes[SERIAL_NUMBER_COL].unique())))
    print('len(df_env_1): {} ({})'.format(len(df_env_1),
                                          df_env_1.iloc[:,0].notnull().sum()))
    print('len(df_env_2): {} ({})'.format(len(df_env_2),
                                          df_env_2.iloc[:,0].notnull().sum()))

    unnamed_columns_1 = [i for i in df_env_1.columns if 'Unnamed' in i]
    if len(unnamed_columns_1) > 0:
        print(unnamed_columns_1)
        check_column_names.append(file)

    unnamed_columns_2 = [i for i in df_env_2.columns if 'Unnamed' in i]
    if len(unnamed_columns_2) > 0:
        print(unnamed_columns_2)
        check_column_names.append(file)

    if data is None:
        data = pd.concat([df_env_1, df_env_2], ignore_index=True)
    else:
        data = pd.concat([data, df_env_1, df_env_2], ignore_index=True)

    if data is not None:
        data.to_csv(join(path, csv_file_name), sep=';')



print()
if data is not None:
    print(data.info())

print('check_column_names:', check_column_names)

if data is not None:
    data.to_csv(join(path, csv_file_name), sep=';')
