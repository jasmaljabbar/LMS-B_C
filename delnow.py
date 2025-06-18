from backend import utils

password = "Coimbatore"
hashed_password = utils.hash_password(password)
print(hashed_password)
