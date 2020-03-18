from little_pger import LittlePGer
import configurations


class dbprocess:
    def __init__(self, connection):
        self.conn = connection

        print('Connecting to the PostgreSQL database...')

    def select(self, table_name, where_field, ):
        pg = LittlePGer(conn=self.conn, commit=False)
        result = pg.select(table_name, where=where_field)
        return result

    def insert(self, table_name, values_list):
        result = ''
        with LittlePGer(conn=self.conn, commit=True) as pg:
            result = pg.insert(table_name, values=values_list, return_id=True)
        return result

    # def __del__(self):
    #     if self.conn is not None:
    #         print(" Closing Connection....")
    #         self.conn.close()
    #         print("  Connection....", self.conn)
