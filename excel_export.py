import xlsxwriter as xlsx

workbook = xlsx.Workbook('Exported_data.xlsx')
worksheet = workbook.add_worksheet('Average_data_1')

row = 0
col = 0
# Write headers
worksheet.write(row, col, 'Разность фаз')
worksheet.write(row, col + 1, 'Частота 1 канала')
worksheet.write(row, col + 2, 'Частота 2 канала')
worksheet.write(row, col + 3, 'Амплитуда 1 канала')
worksheet.write(row, col + 4, 'Амплитуда 2 канала')
worksheet.write(row, col + 5, 'Дистанция')
row += 1
col = 0

with open("measurements.txt", "r") as f:
    lines = f.readlines()
    for line in lines:
        line = line.strip("\n")
        elements = line.split(":")
        for element in elements:
            worksheet.write(row, col, float(element))
            col += 1
        row += 1
        col = 0


# Add new worksheet

worksheet2 = workbook.add_worksheet('All points')
row = 0
col = 0
# Write headers
worksheet2.write(row, col, 'Разность фаз')
worksheet2.write(row, col + 1, 'Частота 1 канала')
worksheet2.write(row, col + 2, 'Частота 2 канала')
worksheet2.write(row, col + 3, 'Амплитуда 1 канала')
worksheet2.write(row, col + 4, 'Амплитуда 2 канала')
worksheet2.write(row, col + 5, 'Дистанция')
row += 1
col = 0

with open("measurements_all_points.txt", "r") as f:
    lines = f.readlines()
    for line in lines:
        line = line.strip("\n")
        elements = line.split(":")
        for element in elements:
            worksheet2.write(row, col, float(element))
            col += 1
        row += 1
        col = 0

workbook.close()
