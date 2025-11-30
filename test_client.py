from client.client import (
    set_server,
    calibrations_upload, calibrations_list, calibrations_download, calibrations_get_latest,
    results_upload, results_download,unzip_bytes_to_folder,test,results_list,set_best_run, get_best_run,
    get_best_n_runs,upload_all_calibrations,upload_all_experiment_runs,print_table
)




# use the api token in place of "very-secret-token"
set_server(server_url="http://127.0.0.1:5050",api_token="secret-token")



# upload_all_calibrations("../CQT-reporting/data/calibrations")

# upload_all_experiment_runs("../CQT-reporting/data")

print_table(calibrations_list())



calibrations_download(hashID="2447f0fad33dfea493b4e7bc4143c8bd2e28d979",output_folder="./download_data_test/calibrations")

calibrations_download(hashID="1e1f7e1d1af58009eda1986bb3689e6b9b2356b6",output_folder="./download_data_test/calibrations")

print_table(results_list(hashID="2447f0fad33dfea493b4e7bc4143c8bd2e28d979"))

results_download(hashID="2447f0fad33dfea493b4e7bc4143c8bd2e28d979",runID="20251111023316",output_folder="./download_data_test")

# set_best_run(calibrationHashID=latest["hashID"],runID='testrun4') 

# Mark a few best runs over time
# set_best_run("cal_hash_A", "run_001")
# set_best_run("cal_hash_B", "run_002")
# set_best_run("cal_hash_A", "run_003")


# Get the most recent best run
# cal_hash, run_id, ts = get_best_run()
# print("Current best:", cal_hash, run_id, ts)

# Get the last 5 best runs
# history = get_best_n_runs(5)
# for cal_hash, run_id, ts in history:
#     print("Best at:", ts, "->", cal_hash, run_id)

# print(get_best_run())
