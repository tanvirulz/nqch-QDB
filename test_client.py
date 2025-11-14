from client.client import (
    set_server,
    calibrations_upload, calibrations_list, calibrations_download, calibrations_get_latest,
    results_upload, results_download,unpack,test,results_list,set_best_run, get_best_run,
    get_best_n_runs
)



# use the api token in place of "very-secret-token"
# set_server(server_url="http://127.0.0.1:5050",api_token="secret-token")

# calibrations_upload(hashID="9848c933bfcafbb8f81c940f504b893a2fa6ac26",notes="test6",files=["/Users/tanvir/Documents/work/git.nosync/nqch-QDB/data/9848c933bfcafbb8f81c940f504b893a2fa6ac23/sinq20/calibration.json","/Users/tanvir/Documents/work/git.nosync/nqch-QDB/data/9848c933bfcafbb8f81c940f504b893a2fa6ac23/sinq20/parameters.json"])
# # items = calibrations_list()

# #notes, fname, created_at, zip_bytes = calibrations_download("9848c933bfcafbb8f81c940f504b893a2fa6ac23")
# #print (notes, fname, created_at)
# #unpack(fname, zip_bytes)
# # print (calibrations_list())
# # print (calibrations_get_latest())
# latest = calibrations_get_latest()

# print (latest)
# print (latest["hashID"])

# resp = results_upload(
#     hashID=latest["hashID"],
#     name="marmin2",
#     notes="second result test",
#     runID="testrun4",
#     files=["./data/mermin/9848c933bfcafbb8f81c940f504b893a2fa6ac23/data_mermin_3q.json",
#            "./data/mermin/9848c933bfcafbb8f81c940f504b893a2fa6ac23/results.json"]
# )

# print (resp)

# print (results_list(latest["hashID"]))
# resp = results_download(hashID=latest["hashID"],name="marmin2",runID="testrun2",)
# print (resp)

# set_best_run(calibrationHashID=latest["hashID"],runID='testrun4') 

# Mark a few best runs over time
set_best_run("cal_hash_A", "run_001")
set_best_run("cal_hash_B", "run_002")
set_best_run("cal_hash_A", "run_003")

# Get the most recent best run
cal_hash, run_id, ts = get_best_run()
print("Current best:", cal_hash, run_id, ts)

# Get the last 5 best runs
history = get_best_n_runs(5)
for cal_hash, run_id, ts in history:
    print("Best at:", ts, "->", cal_hash, run_id)

print(get_best_run())
