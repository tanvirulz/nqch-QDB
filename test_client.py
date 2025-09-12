from client.client import (
    set_server,
    calibrations_upload, calibrations_list, calibrations_download, calibrations_get_latest,
    results_upload, results_download,unpack,test,results_list
)

#test()

set_server(server_url="http://127.0.0.1:5050",api_token="very-secret-token")



#calibrations_upload(hashID="9848c933bfcafbb8f81c940f504b893a2fa6ac23",notes="test5",files=["/Users/tanvir/Documents/work/git.nosync/nqch-QDB/data/9848c933bfcafbb8f81c940f504b893a2fa6ac23/sinq20/calibration.json","/Users/tanvir/Documents/work/git.nosync/nqch-QDB/data/9848c933bfcafbb8f81c940f504b893a2fa6ac23/sinq20/parameters.json"])
#items = calibrations_list()

#notes, fname, created_at, zip_bytes = calibrations_download("9848c933bfcafbb8f81c940f504b893a2fa6ac23")
#print (notes, fname, created_at)
#unpack(fname, zip_bytes)
#print (calibrations_list())
#print (calibrations_get_latest())
latest = calibrations_get_latest()

#print (latest)
print (latest["hashID"])

# resp = results_upload(
#     hashID=latest["hashID"],
#     name="marmin2",
#     notes="second result test",
#     files=["./data/mermin/9848c933bfcafbb8f81c940f504b893a2fa6ac23/data_mermin_3q.json",
#            "./data/mermin/9848c933bfcafbb8f81c940f504b893a2fa6ac23/results.json"]
# )

# print (resp)

print (results_list(latest["hashID"]))