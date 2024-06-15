import sqlite3

# Kết nối đến cơ sở dữ liệu SQLite
conn = sqlite3.connect('iot.db')
cursor = conn.cursor()

try:
    # Xóa tất cả dữ liệu trong bảng sensor_data
    cursor.execute("DELETE FROM sensor_data")
    conn.commit()
    print("Đã xóa tất cả dữ liệu trong bảng sensor_data")
except sqlite3.Error as error:
    print("Lỗi khi xóa dữ liệu:", error)
finally:
    # Đóng kết nối đến cơ sở dữ liệu
    if conn:
        conn.close()