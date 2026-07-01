import pandas as pd


# parse headers for common details
def parse_headers(workbook, headers):
    try:
        rows, cols = workbook.shape
        outheaders = []
        for row_num in range(rows):
            for col_num in range(cols):
                cell_value = workbook.iloc[row_num, col_num]
                if pd.isna(cell_value):
                    continue
                for i in range(len(headers)):
                    # Each header is in format ["headername", "C" or "R"] to determine whether the value is in the row or in the column
                    if headers[i][0].strip() == str(cell_value).strip():
                        if headers[i][1] == "C":
                            row_position = row_num + 1
                            col_position = col_num
                            curr_cell = workbook.iloc[row_position, col_position]
                            while row_position < cols:
                                if pd.notna(curr_cell) and pd.notnull(curr_cell):
                                    break
                                row_position += 1
                        #write elif to extract value from same row but after skipping 2 cols and get 2 columns value for single header  Total in Account Currency 
                        elif headers[i][1] == "L":
                            row_position = row_num
                            col_position1 = col_num + 3
                            col_position2 = col_num + 4
                            curr_cell1 = workbook.iloc[row_position, col_position1]
                            curr_cell2 = workbook.iloc[row_position, col_position2]
                            while col_position1 < cols:
                                if pd.notna(curr_cell1) and pd.notnull(curr_cell1):
                                    break
                                col_position1 += 1
                            while col_position2 < cols:
                                if pd.notna(curr_cell2) and pd.notnull(curr_cell2):
                                    break
                                col_position2 += 1
                            curr_cell = str(curr_cell1) + "|" + str(curr_cell2)
                        else:
                            row_position = row_num
                            col_position = col_num + 1
                            while col_position < cols:
                                curr_cell = workbook.iloc[row_position, col_position]
                                if pd.notna(curr_cell) and pd.notnull(curr_cell):
                                    break
                                col_position += 1
                        outheaders.append(curr_cell)
                        break
        return outheaders
    except Exception as e:
        print("Header parsing error:", e)
        return None
