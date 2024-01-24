#!/usr/bin/python
import sys, os, subprocess,fnmatch, shutil, csv, re, datetime
import re
from ansi2html import Ansi2HTMLConverter
from bs4 import BeautifulSoup
import json
import copy
from transformers import RobertaTokenizer, T5ForConditionalGeneration

TEST_SAMPLE_WITH_ERROR_PATH="./repair/train_sample"
REPAIR_PATH="./repair"
NUMBER_OF_ITERATIONS_PER_LOCATION = 1
PROJECT_CLONE_PATH = "./projects"
CLONE_FILE_NAME="clone"
PREVIOUS_ITERATION_CLONE="clone_previous"
NO_OF_TEST_CASES = 3

BASH_COMPLIE_PATH = "../../../../bash/compile.sh"
BASH_TEST_PATH = "../../../../bash/run_test.sh"
POM_PATH="./"
NUM_BEAMS = 5
num_return_sequences = 5

TEST_GENERATOR_PATH ="./test_case_generator_2"
TEST_GENERATION_BUGGY_FILE_PATH = "./repair"

def remove_bug_annotation(sample):
    a =  sample["ctxs"][0]["txt"]
    sample["ctxs"][0]["txt"] = a[:a.find("<BUG>")]+"<extra_id_0>"+a[a.find("</BUG>")+6:]
    return sample
    
def remove_html_tags(text):
    soup = BeautifulSoup(text, 'html.parser')
    return soup.get_text()

def getHtmlErrors(result):
    converter = Ansi2HTMLConverter(inline=True)
    html_errors = converter.convert(result.stdout)
    return html_errors

def getErrorMsg(error_msg):
    return extractCompilationError(remove_html_tags(getHtmlErrors(error_msg)))
    
def fix_using_code_t5(sample):
    text =  sample["ctxs"][0]["txt"]
    tokenizer = RobertaTokenizer.from_pretrained('Salesforce/codet5-small')
    model = T5ForConditionalGeneration.from_pretrained('Salesforce/codet5-small')
    input_ids = tokenizer(text, return_tensors="pt").input_ids
    generated_ids = model.generate(input_ids, max_length=20,num_beams=NUM_BEAMS, num_return_sequences=num_return_sequences)
    predictions = []
    for i, output in enumerate(generated_ids):
        decoded_output = tokenizer.decode(output, skip_special_tokens=True)
        predictions.append(decoded_output)
        print("Prediction ", i, ": ", decoded_output)
    # prediction = tokenizer.decode(generated_ids[0], skip_special_tokens=True)
    # print("PREDICTION --> ",prediction)
    return predictions



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



def getTestFailureError(path):
    os.chdir(path)

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
        os.chdir("../../../../")
        return error_msg.strip(", ")
    
    except:
        os.chdir("../../../../")
        return None



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




def apply_patch(path, buggy_input, patch):

    if "buggy_line_no" not in buggy_input or "file_path" not in buggy_input:
        exit()

    start_line, end_line = buggy_input["buggy_line_no"]

    file =  path+"/"+buggy_input["file_path"]

    with open(file, 'r') as f:
        lines = f.readlines()

    index =0
    patched_lines=[]
    while index < len(lines):
        if index == start_line-1:
            for i in range(start_line-1,end_line-1):
                patched_lines.append("\n")
                index+=1
            if start_line!=end_line:
                patched_lines.pop()
            if patch == "[Delete]":
                patched_lines.append("\n")
            else:
                patched_lines.append(patch+"\n")
        patched_lines.append(lines[index])
        index+=1
    
    with open(file, 'w') as f:
        f.write("".join(patched_lines))

def getCompileResult(projectCompileDir):
    os.chdir(projectCompileDir)
    # result = subprocess.run(['bash', BASH_COMPLIE_PATH,"./"], capture_output=True, text=True)
    result = subprocess.run(['defects4j', "compile"], capture_output=True, text=True)
    os.chdir("../../../../")
    return result

def getTestRunResults(projectCompileDir):
    os.chdir(projectCompileDir)
    result = subprocess.run(['defects4j', "test"], capture_output=True, text=True)

    os.chdir("../../../../")
    if not result.stdout:
        print("COMIPLATION ERROR")
    return result

def getFailTestCount(text):
    pattern = r"Failing tests: (\d+)"

    match = re.search(pattern, text)

    if match:
        failing_test_count = int(match.group(1))
        return failing_test_count
    else:
        return 0

def find_java_test_folder(project):
    if project=="Chart":
        return "/tests/org/jfree"
    if project=="Closure":
        return "/test/com/google/javascript/jscomp"
    if project=="Lang":
        return "/src/test/java/org/apache/commons/lang3"



def test_generation(project,bug,generated_patch,buggy_input):
    return False



def is_correct(project,bug,generated_patch,buggy_input):
    curr_itertaion_project_path = REPAIR_PATH+"/"+project+"/"+bug+"/"+CLONE_FILE_NAME+"/"
    prev_itertaion_project_path = REPAIR_PATH+"/"+project+"/"+bug+"/"+PREVIOUS_ITERATION_CLONE+"/"
    # compilation_result =  getCompileResult(curr_itertaion_project_path)
    # if checkForCompilationError(compilation_result.stdout):
    #     error_msg = getErrorMsg(compilation_result)
    #     if error_msg:
    #         return error_msg, "COMPILE_ERROR"

    curr_test_result =  getTestRunResults(curr_itertaion_project_path)

    if not curr_test_result.stdout:
        return  "compilation error", "COMPILE_ERROR" #TODO
    
    curr_tests=curr_test_result.stdout.split(" - ")
    curr_failing_test_count =getFailTestCount(curr_test_result.stdout)

    if curr_failing_test_count == 0:
        return "COMPLETED", "COMPLETED"
    
    error_msg = getTestFailureError(curr_itertaion_project_path)

    
    prev_test_result =  getTestRunResults(prev_itertaion_project_path)

    if not prev_test_result.stdout:
        return  error_msg , "PARTIALLY" #TODO
    
    prev_failing_test_count =getFailTestCount(prev_test_result.stdout)

    if prev_failing_test_count<curr_failing_test_count:
        return  error_msg , "PARTIALLY"
    
    if test_generation(project,bug,generated_patch,buggy_input):
        return  error_msg , "PARTIALLY"
    
    return error_msg, None


def generate_FID(buggy_input):
    print(buggy_input)
    return fix_using_code_t5(buggy_input)
 

def copy_project(project,bug,generated_patches):
    clone_path = REPAIR_PATH+"/"+project+"/"+bug+"/"+CLONE_FILE_NAME
    previous_clone_path = REPAIR_PATH+"/"+project+"/"+bug+"/"+PREVIOUS_ITERATION_CLONE
    clear_path(clone_path)
    # os.system("cp -r "+PROJECT_CLONE_PATH+"/"+project+bug+"/* "+clone_path)
    shutil.copytree(PROJECT_CLONE_PATH+"/"+project+bug, clone_path)

    clear_path(previous_clone_path)
    # os.system("cp -r "+PROJECT_CLONE_PATH+"/"+project+bug+"/* "+previous_clone_path)
    shutil.copytree(PROJECT_CLONE_PATH+"/"+project+bug, previous_clone_path)

    for i in range(len(generated_patches)):
        apply_patch( clone_path ,test_samples[i],generated_patches[i])

    for i in range(len(generated_patches)):
        apply_patch(previous_clone_path ,test_samples[i],generated_patches[i])


def write_to_file(project,bug,generated_patches,correctness,iteration,location):

    if location is not None and not os.path.exists(REPAIR_PATH+"/"+project+"/"+bug+"/"+"FL_"+location):
        os.system("mkdir "+REPAIR_PATH+"/"+project+"/"+bug+"/"+"FL_"+location)
    if iteration is not None and not os.path.exists(REPAIR_PATH+"/"+project+"/"+bug+"/"+"FL_"+location+"/"+"IT_"+iteration):
        os.system("mkdir "+REPAIR_PATH+"/"+project+"/"+bug+"/"+"FL_"+location+"/"+"IT_"+iteration)
    
    if correctness=="COMPLETED":
        with open("./"+project+"_"+bug+"_complete.json", 'w') as outfile:
            json.dump(generated_patches, outfile)
        return
    if correctness=="PARTIALLY":
        with open("./"+project+"_"+bug+"_partially.json", 'w') as outfile:
            json.dump(generated_patches, outfile)

    

def repair(generated_patches=[],sample_index=0,COMPLETED=False,exsample=None):
    print("++++++++++++++++++++++++++")
    print(generated_patches)
    print(len(generated_patches))
    print("++++++++++++++++++++")
    if sample_index >= len(test_samples):
        if COMPLETED:
            write_to_file(project,bug,generated_patches,"COMPLETED",None,None)
            exit()
        return 
    if exsample==None:
        sample = copy.deepcopy(test_samples[sample_index])
    else:
        sample = copy.deepcopy(exsample)
    sample = remove_bug_annotation(sample)

    iteration =0
    while iteration < NUMBER_OF_ITERATIONS_PER_LOCATION:
        generated_patch = generate_FID(sample)
        for patch_index in range(len(generated_patch)):
            patch = generated_patch[patch_index]
            copy_project(project,bug,generated_patches)
            apply_patch( REPAIR_PATH+"/"+project+"/"+bug+"/"+CLONE_FILE_NAME,sample, patch)
            correctness_with_error = is_correct(project,bug,patch,sample)
            if correctness_with_error[1] =="COMPLETED":
                generated_patches.append(patch)
                return repair(generated_patches,len(test_samples),True,None)
            
            elif correctness_with_error[1]=="PARTIALLY":
                temp_sample = copy.deepcopy(sample)
                temp_sample["err"]=correctness_with_error[0]
                repair(generated_patches+[patch],sample_index+1,False,temp_sample)

            else:
                temp_sample = copy.deepcopy(sample)
                temp_sample["err"]=correctness_with_error[0]
                repair(generated_patches+[patch],sample_index+1,False)
        iteration+=1

def clear_path(path):
    if os.path.exists(path):
        os.system("rm -rf "+path)
def clear_and_recreate_path(path):
    # if os.path.exists(path):
        # os.system("rm -rf "+path)
    os.system("mkdir "+path)

def create_repair_path(path):
    if not os.path.exists(path):
        os.system("mkdir "+path)


def read_train_sample(path):
    with open(path, 'r') as file:
        data = json.load(file)
    return data

if __name__ == '__main__':
    global generated_patches_fid,project,bug,test_samples
    project=sys.argv[1]
    bug=sys.argv[2]
    create_repair_path(REPAIR_PATH+"/"+project)
    clear_and_recreate_path(REPAIR_PATH+"/"+project+"/"+bug)
    test_samples = read_train_sample(TEST_SAMPLE_WITH_ERROR_PATH+"/"+project+"/"+bug+".json")
    for i in test_samples:
        for j in i["ctxs"]:
            print(j["txt"])
        # print(i["ctxs"])
    repair()
    
    
