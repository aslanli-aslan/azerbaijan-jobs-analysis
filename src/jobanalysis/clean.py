

def parse_view_count(row):
    if isinstance(row, str):
        row = float(row[:-1]) * 1000
    return int(row)