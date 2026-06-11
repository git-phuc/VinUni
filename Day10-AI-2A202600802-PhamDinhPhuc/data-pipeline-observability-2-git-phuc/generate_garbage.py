import csv

def generate_garbage_data():
    """
    Generates a csv file with common 'Data Quality' issues.
    """
    data = [
        ['id', 'product', 'price', 'category'],
        [1, 'Laptop', 1200, 'electronics'],
        [1, 'Banana', 2, 'fruit'], # Duplicate ID
        [2, 'Broken Chair', 'ten dollars', 'furniture'], # Wrong type
        [3, 'Nuclear Reactor', 999999, 'electronics'], # Extreme Outlier
        [None, 'Ghost Item', 0, None], # Null values
    ]
    
    with open('garbage_data.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)
    print("garbage_data.csv has been created with 'Poisoned' records.")

if __name__ == "__main__":
    generate_garbage_data()
