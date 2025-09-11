from client.client import (
    set_server,
    calibrations_upload, calibrations_list, calibrations_download, calibrations_get_latest,
    results_upload, results_download,unpack,test
)

#test()

set_server("http://127.0.0.1:5050")


#calibrations_upload(hashID="9848c933bfcafbb8f81c940f504b893a2fa6ac23",notes="test-calibration", ["/Users/tanvir/Documents/work/git.nosync/nqch-QDB/data/9848c933bfcafbb8f81c940f504b893a2fa6ac23/sinq20/calibration.json","/Users/tanvir/Documents/work/git.nosync/nqch-QDB/data/9848c933bfcafbb8f81c940f504b893a2fa6ac23/sinq20/parameters.json"])
#calibrations_upload(hashID="9848c933bfcafbb8f81c940f504b893a2fa64c23",notes="test2",files=["/Users/tanvir/Documents/work/git.nosync/nqch-QDB/data/9848c933bfcafbb8f81c940f504b893a2fa6ac23/sinq20/calibration.json","/Users/tanvir/Documents/work/git.nosync/nqch-QDB/data/9848c933bfcafbb8f81c940f504b893a2fa6ac23/sinq20/parameters.json"])
#items = calibrations_list()

notes, fname, zip_bytes = calibrations_download("9848c933bfcafbb8f81c940f504b893a2fa6ac23")
unpack("./calib_abc123", zip_bytes)
