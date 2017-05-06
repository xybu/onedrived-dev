import re

site = 'https://fatecspgov-my.sharepoint.com/personal/mario_apra_fatec_sp_gov_br/Documents'


tenant = site[8:site.find('-my.sharepoint.com/')]

print('tenant: ' + tenant)

#https://{tenant}-my.sharepoint.com/
#total: 27
inicio = 27 + len(tenant)
teste = site[inicio:]
print('teste1: ' + teste)

teste2 = teste[:teste.find('/')]
print('teste2: ' + teste2)


teste3 = teste[len(teste2) + 1:]
teste3 = teste3[:teste3.find('/')]

print ('teste3: ' + teste3)

