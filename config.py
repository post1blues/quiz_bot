from environs import Env


env = Env()
env.read_env()

TG_TOKEN = env('TG_TOKEN')
VK_TOKEN = env('VK_TOKEN')
QUIZ_FOLDER = env('QUIZ_FOLDER')

REDIS_HOST = env('REDIS_HOST')
REDIS_PORT = env('REDIS_PORT')
REDIS_PASSWORD = env('REDIS_PASSWORD')
