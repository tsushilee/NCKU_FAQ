import re

s = "try this my ip isdhaha140.116.297.172"
ip = re.findall( r'[0-9]+(?:\.[0-9]+){3}', s )

print(len(ip))
