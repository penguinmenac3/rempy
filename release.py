import os
import json

TEST_RESULTS_FILENAME = "tests/results.txt"

def run_tests():
    # Runs all functions called test which are in the folder test named "test_*.py"
    # The function has the signature test(old_results: dict, new_results:dict) -> success
    old_results = {}
    new_results = {}
    if os.path.exists(TEST_RESULTS_FILENAME):
        with open(TEST_RESULTS_FILENAME, "r") as f:
            old_results = json.loads(f.read())

    positive = 0
    negative = 0
    failed = []
    tests = []
    if os.path.exists("tests"):
        tests = ["tests." + f.replace(".py", "") for f in os.listdir("tests") if f.startswith("test_") and f.endswith(".py")]#

    for test in tests:
        test_case = __import__(test, fromlist=["*"])
        for k in test_case.__dict__:
            if k.startswith("test_"):
                print("Running: {}.{}".format(test, k))
                success = test_case.__dict__[k](old_results, new_results)
                if success:
                    print("Passed: {}.{}".format(test, k))
                    positive += 1
                else:
                    print("Failed: {}.{}".format(test, k))
                    negative += 1
                    failed.append("{}.{}".format(test, k))
                print()
    
    with open(TEST_RESULTS_FILENAME, "w") as f:
        f.write(json.dumps(new_results, indent=4, sort_keys=True))

    print("Successfull/Failed: {}/{}".format(positive, negative))
    print("Failed Tests:")
    for name in failed:
        print("- {}".format(name))
    return negative == 0

def update_setup_py(major_release=False, minor_release=False):
    lines = ""
    with open("setup.py", "r") as f:
        lines = f.readlines()
    for i in range(len(lines)):
        if lines[i].startswith("__version__"):
            version = lines[i].split("=")[-1]
            version = version.split("'")[1].split(".")
            version[2] = str(int(version[2]) + 1)
            if minor_release:
                version[2] = '0'
                version[1] = str(int(version[1]) + 1)
            if major_release:
                version[2] = '0'
                version[1] = '0'
                version[0] = str(int(version[0]) + 1)
            version = ".".join(version)
            lines[i] = "__version__ = '" + version + "'\n"
    with open("setup.py", "w") as f:
        f.writelines(lines)
    
    return version

def commit_and_push(version):
    # Add changed setup and the test results.
    os.system("git add setup.py")
    os.system("git add " + TEST_RESULTS_FILENAME)
    os.system("git commit -m 'Version " + version + ".'")
    os.system("git push")
    # Also create tag for the version
    os.system("git tag " + version)
    os.system("git push origin --tags")

def pip_publish():
    os.system("python setup.py bdist_wheel")
    os.system("twine upload dist/*")

def main(major_release=False, minor_release=False, dry_run=False):
    if run_tests():
        if dry_run:
            print("All tests successfull.")
        else:
            version = update_setup_py(major_release, minor_release)
            commit_and_push(version)
            pip_publish()
            print("Released")
    else:
        print("One or more tests failed!")

main(major_release=True, minor_release=True, dry_run=True)

