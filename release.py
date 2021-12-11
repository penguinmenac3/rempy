import os

def run_tests():
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
                try:
                    success = test_case.__dict__[k]()
                except Exception as e:
                    print("Exception:")
                    print(e)
                    success = False
                if success:
                    print("Passed: {}.{}".format(test, k))
                    positive += 1
                else:
                    print("Failed: {}.{}".format(test, k))
                    negative += 1
                    failed.append("{}.{}".format(test, k))
                print()

    print("Successfull/Failed: {}/{}".format(positive, negative))
    if len(failed) > 0:
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
    os.system("git commit -m 'Version " + version + ".'")
    os.system("git push")
    # Also create tag for the version
    os.system("git tag " + version)
    os.system("git push origin --tags")

def pip_publish():
    os.system("python setup.py bdist_wheel")
    os.system("twine upload dist/*")

def main(major_release=False, minor_release=False, dry_run=False):
    print("Test: " if dry_run else "Release: ", end="")
    if major_release:
        print("Major")
    elif minor_release:
        print("Minor")
    else:
        print("Bugfix")
    dry_run = True
    if run_tests():
        if not dry_run:
            version = update_setup_py(major_release, minor_release)
            commit_and_push(version)
            pip_publish()
            print("Released")
    else:
        print("One or more tests failed! Cannot release!")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--major", action="store_true", help="If this is a major release, i.e. api changed.")
    parser.add_argument("--minor", action="store_true", help="If this is a minor release, i.e. added features.")
    parser.add_argument("--test", action="store_true", help="Do not actually do the release, just test.")
    args = parser.parse_args()
    main(major_release=args.major, minor_release=args.minor, dry_run=args.test)
