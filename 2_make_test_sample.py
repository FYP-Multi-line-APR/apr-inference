#!/usr/bin/python
import sys, os, subprocess,fnmatch, shutil, csv, re, datetime
import re
from ansi2html import Ansi2HTMLConverter
from bs4 import BeautifulSoup
import json

BASH_COMPLIE_PATH = "../../bash/compile.sh"
BASH_TEST_PATH = "../../bash/run_test.sh"
POM_PATH="./"
REPAIR_PATH="../../repair"
TEST_SAMPLE_PATH="../../defects4j-setup/train-data"
TEST_SAMPLE_WITH_ERROR_PATH="../../repair/train_sample"




NO_OF_TEST_CASES = 3
def remove_html_tags(text):
    soup = BeautifulSoup(text, 'html.parser')
    return soup.get_text()

def getHtmlErrors(result):
    converter = Ansi2HTMLConverter(inline=True)
    html_errors = converter.convert(result.stdout)
    return html_errors

def getErrorMsg(error_msg):
    return extractCompilationError(remove_html_tags(getHtmlErrors(error_msg)))
    


def extract_expected_actual(input_string):
    pattern = r'Expected: is "(.*?)"\s*but: was "(.*?)"'
    matches = re.finditer(pattern, input_string, re.DOTALL)
    
    result_list = []
    for i, match in enumerate(matches):
        if i < NO_OF_TEST_CASES:
            expected = match.group(1)
            actual = match.group(2)
            result_list.append(f'Expected: is "{expected}"\n     but: was "{actual}"')
        else:
            break
    
    return "\n".join(result_list)



def getTestFailureError():
    try:
        with open('failing_tests', 'r') as file:
            data = file.readlines()
        error_msg=""
        error_msg_count = 0
        for index in range(len(data)):
            if data[index].startswith('---'):
                if index+1 < len(data):
                    error_line = data[index+1]
                    seperator_index = error_line.find(':')
                    error_type = error_line[:seperator_index].split('.')[-1]
                    if  error_type+ error_line[seperator_index+1:].strip() not in error_msg:
                        error_msg += error_type+ error_line[seperator_index+1:].strip()+", "
                        error_msg_count += 1 
                        if error_msg_count == NO_OF_TEST_CASES:
                            break
        return error_msg.strip(", ")
    except:
        return None

def find_pom_path(folder):
    for root, dirs, files in os.walk(folder):
        #print(dirs)
        for file in files:
            # print(file)
            if file.endswith("pom.xml"):
                path_to_pom =  os.path.join(root, file)
                return path_to_pom[:-7]
    return None


def getCompileResult(projectCompileDir):
    # compile directory
    result = subprocess.run(['bash', BASH_COMPLIE_PATH,projectCompileDir], capture_output=True, text=True)
    # print(result.stdout)
    return result

def getTestRunResults():
    # execute tests and get results
    result = subprocess.run(['defects4j', "test"], capture_output=True, text=True)
    # print(result.stdout)

    return result

def checkForCompilationError(result):
    pattern = r'COMPILATION ERROR'
    match = re.search(pattern, result)
    if match:
        return True
    else:
        return False


def extractCompilationError(result):
    if "Compilation failure" in result:
        result = result.strip()
        result = result.split("Compilation failure")[-1]
        if "->" not in result:
            return None
        
        result = result.split("->")[0]
        result = result.replace("[ERROR] ", "")
        result = result.strip()
        error_msg = ""
        for i in result.split("\n"):
            removed_spaces = i.strip(" ")
            if removed_spaces.startswith("/"):
                if ":" in removed_spaces:
                    removed_spaces = removed_spaces.split(":")[-1]
                    if "]" in removed_spaces:
                        removed_spaces = removed_spaces.split("]")[-1]
                        removed_spaces = removed_spaces.strip()
                    else:
                        removed_spaces = removed_spaces.strip()
                    if removed_spaces != "" and removed_spaces not in error_msg:
                        error_msg += removed_spaces+", "
                
            elif "symbol" in removed_spaces or "reason" in removed_spaces:
                if removed_spaces not in error_msg:
                    error_msg += removed_spaces+", "
        if error_msg == "":
            return None
        
        return error_msg.strip(", ")
    else:
        return None

def remove_newlines(text):
    text=  text.strip()
    text = text.replace("\n", ", ")
    return re.sub(r'\s+', ' ', text)

# def run_git_show():
#     try:
#         # Run the git show command
#         result = subprocess.run(['git', 'show'], check=True, stdout=subprocess.PIPE, text=True)
#         print(result.stdout)

#         diff_lines = [line for line in result.stdout.split('\n') ]

#         # Extract consecutive blocks of '+' and '-' lines
#         plus_blocks = []
#         minus_blocks = []
#         prev_minus=False
#         prev_plus  =False
#         for line in diff_lines:

#             if line.startswith('+') and line[1:].strip():
                
#                 prev_minus=False
#                 if not prev_plus:
#                     plus_blocks.append(line[1:]+"\n")
#                     prev_plus=True
#                 else:
#                     plus_blocks[-1] += line[1:]+"\n"

#             elif line.startswith('-') and line[1:].strip():
               
#                 prev_plus=False
#                 if not prev_minus:
#                     prev_minus=True
#                     minus_blocks.append(line[1:]+"\n")
#                 else:
#                     minus_blocks[-1] += line[1:]+"\n"
#             else:
#                 prev_plus=False
#                 prev_minus=False
#         return plus_blocks, minus_blocks

#     except subprocess.CalledProcessError as e:
#         print(f"Error running 'git show': {e}")

def getFailTestCount(text):
    pattern = r"Failing tests: (\d+)"

# Use re.search to find the match in the text
    match = re.search(pattern, text)

    # Check if a match is found and extract the failing test count
    if match:
        failing_test_count = int(match.group(1))
        return failing_test_count
    else:
        return 0

def addErroMsg(path,project,bug,save_path,error_msg):
    try:
        if not os.path.exists(save_path):
            os.system("mkdir "+save_path)
        # if os.path.exists(save_path+"/"+project):
        #     os.system("rm -rf "+save_path+"/"+project)
        os.system("mkdir "+save_path+"/"+project)
        
        project_path = path+"/"+project+"/"+bug+".json"
        with open(project_path,"r") as json_file:
            content=json_file.read()
        content = eval(content)
        bug_id = 1
        for sample in content:
            sample["err"]=error_msg
            sample["id"]=bug_id
            bug_id+=1
        save_file = save_path+"/"+project+"/"+bug+".json"

        with open(save_file,"w") as save_json:
            json.dump(content, save_json)

    except Exception as e:
        print(e)
        pass

def create_repair_path(path):
    if not os.path.exists(path):
        # os.system("rm -rf "+path)
        os.system("mkdir "+path)
        

if __name__ == '__main__':
    print("STARTED COPPIIING............")
    project=sys.argv[1]
    bug=sys.argv[2]
    project_path = "./projects/"+project+bug
    
    os.chdir(project_path)
    create_repair_path(REPAIR_PATH)


    pom_path = POM_PATH
    if not pom_path:
        print("No .pom file found in the specified folder.")
        exit(1)


    # plus_blocks, minus_blocks =  run_git_show()

    # for i in plus_blocks:
    #     print(i)
    #     print("-------")

    error_msg = ""
    # result = getCompileResult(pom_path)
    # if checkForCompilationError(result.stdout):
    #     error_msg = getErrorMsg(result)
    #     if not error_msg:
    #         print("Compilation error but no error message found\n\n\n\n")
            
    # else:
    #     test_result =  getTestRunResults()
    #     fail_tests = ""
    #     tests=test_result.stdout.split(" - ")
    #     failing_test_count =getFailTestCount(test_result.stdout)
    #     if failing_test_count > 0:
    #         error_msg = getTestFailureError()
    #     print(test_result.stdout)
    #     if not error_msg:
    #         print("No test failure error message found\n\n\n\n")
    # print(error_msg)
    addErroMsg(TEST_SAMPLE_PATH,project,bug,TEST_SAMPLE_WITH_ERROR_PATH,error_msg)
    print("DONE COPPIIING............")



        
    