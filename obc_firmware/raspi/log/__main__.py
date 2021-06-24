import os, logging
"""
dirpath = os.getcwd()
print("current directory is : " + dirpath)
foldername = os.path.basename(dirpath)
print("Directory name is : " + foldername)

os.system("cd ..")
dirpath = os.getcwd()
print("current directory is : " + dirpath)
"""
def main():
	handlers = [logging.FileHandler('log/system.log'), logging.StreamHandler()]
	log_format = '%(asctime)s %(levelname)-8s %(name)-10s %(message)s \t\tThread:%(threadName)-10s FName:%(funcName)s Line#:(%(lineno)d)'
	logging.basicConfig(level=logging.DEBUG,
	 					handlers = handlers,
						format = log_format
						)


	logging.debug('This is a debug message')
	logging.info('This is an info message')
	logging.warning('This is a warning message')
	logging.error('This is an error message')
	logging.critical('This is a critical message')
	logging.exception('Error occurred while Getting Device Code ')


if __name__ == '__main__':
	main()
