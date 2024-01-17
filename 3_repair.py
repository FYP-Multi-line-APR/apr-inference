#!/usr/bin/python
import sys, os, subprocess,fnmatch, shutil, csv, re, datetime
import re
from ansi2html import Ansi2HTMLConverter
from bs4 import BeautifulSoup
import json
import copy

TEST_SAMPLE_WITH_ERROR_PATH="./repair/train_sample"
REPAIR_PATH="./repair"
NUMBER_OF_ITERATIONS_PER_LOCATION = 3
PROJECT_CLONE_PATH = "./projects"
CLONE_FILE_NAME="clone"
PREVIOUS_ITERATION_CLONE="clone_previous"
NO_OF_TEST_CASES = 3

BASH_COMPLIE_PATH = "../../../../bash/compile.sh"
BASH_TEST_PATH = "../../../../bash/run_test.sh"
POM_PATH="./"


TEST_GENERATOR_PATH ="./test_case_generator_2"
TEST_GENERATION_BUGGY_FILE_PATH = "./repair"


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

def find_pom_path(folder):
    for root, dirs, files in os.walk(folder):
        #print(dirs)
        for file in files:
            # print(file)
            if file.endswith("pom.xml"):
                path_to_pom =  os.path.join(root, file)
                return path_to_pom[:-7]
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
    print(buggy_input)

    if "buggy_line_no" not in buggy_input or "file_path" not in buggy_input:
        print("buggy line no not found")
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
    print(os.getcwd())
    print(result)
    print("---------------------\n\n")
    return result

def getTestRunResults(projectCompileDir):
    print(os.getcwd())
    os.chdir(projectCompileDir)
    result = subprocess.run(['defects4j', "test"], capture_output=True, text=True)
    # print(result.stdout)
    os.chdir("../../../../")
    print(os.getcwd())
    print(result.stdout)
    print("---------------------\n\n")
    return result

def getFailTestCount(text):
    pattern = r"Failing tests: (\d+)"

    match = re.search(pattern, text)

    if match:
        failing_test_count = int(match.group(1))
        return failing_test_count
    else:
        return 0
    

# def find_java_test_folder(java_repo_path):
#     # Check if the provided path exists
#     print(os.getcwd())
#     print(java_repo_path)
#     if not os.path.exists(java_repo_path):
#         return None

#     # Walk through the directory tree and find the 'test' or 'tests' folder
#     for root, dirs, files in os.walk(java_repo_path):
#         for dir_name in dirs:
#             if dir_name.lower() == 'test' or dir_name.lower() == 'tests':
#                 return os.path.join(root, dir_name)

#     return None

def find_java_test_folder(project):
    if project=="Chart":
        return "/tests/org/jfree/chart/annotations/junit"
    if project=="Closure":
        return "/test/com/google/javascript/jscomp"
    if project=="Lang":
        return "/src/test/java/org/apache/commons/lang3"




def test_generation(project,bug,generated_patch,buggy_input):
    print(os.getcwd())
    with open(TEST_GENERATOR_PATH+"/generated_patches.json","w") as gp_file:
        json.dump([generated_patch], gp_file)

    with open(TEST_GENERATOR_PATH+"/test_samples.json","w") as ts_file:
        json.dump([buggy_input], ts_file)

    test_path = find_java_test_folder(project)
    if test_path == None:
        print("Test path not found")
        exit()
    print("Test path: ", test_path)
    test_path="/content/apr-inference"+str(test_path)[1:]
    print(test_path)
    
    os.chdir(TEST_GENERATOR_PATH)
    buggy_file_path = "/content/apr-inference"+ TEST_GENERATION_BUGGY_FILE_PATH[1:]+"/"+project+"/"+bug+"/"+PREVIOUS_ITERATION_CLONE+"/"+buggy_input["file_path"]
    project_path= "/content/apr-inference"+ TEST_GENERATION_BUGGY_FILE_PATH[1:]+"/"+project+"/"+bug+"/"+PREVIOUS_ITERATION_CLONE
    command = [
        'python', 'main.py',
        '--buggy_file_path',buggy_file_path,
        '--test_file_dir_path', test_path,
        '--template_file_path', './Templates/template_1.txt',
        '--prompt_dir_path', './prompts',
        '--buggy_line_number', str(buggy_input["buggy_line_no"][0]),
        '--generated_test_files_dir', './generated_test_cases',
        '--project_path',project_path,
        '--temp_dir', './temp',
        '--project_name', PREVIOUS_ITERATION_CLONE,
        '--for_missing_test_class_file_path', './Class/missing_test_class/MissingTestClass.java',
        '--num_of_test_cases', '1',
        '--test_bash_path', './test_run.bash',
        '--test_result_dir_path', './test_results',
        '--extractor_jar_path', './Extractor/target/Extractor-1.0-SNAPSHOT.jar',
        '--injector_jar_path', './Injector/target/Injector-1.0-SNAPSHOT.jar'
    ]
    # Run the command
    result = subprocess.run(command, capture_output=True, text=True)

    # Print the output
    print("Command Output:")
    print(result.stdout)
    print("---------------------\n\n")
    print("Command Error:")
    print(result.stderr)
    print("---------------------\n\n")



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
    
    test_generation(project,bug,generated_patch,buggy_input)
    
    return error_msg, None


def generate_FID(buggy_input):
    file_path =  REPAIR_PATH+"/"+project+"/"+bug+"/input.json"
    with open(file_path, "w") as f:
        json.dump([buggy_input],f)
    subprocess.run(['chmod', '+x', '/content/drive/MyDrive/23_FYP-Multi Line APR/FiD-model/model_we/checkpoint/my_experiment/checkpoint/best_dev'])
    command = [
        'python', './fid/new_fid/get_predicitons.py',
        '--model_path', '/content/drive/MyDrive/23_FYP-Multi Line APR/FiD-model/model_we/checkpoint/my_experiment/checkpoint/best_dev',
        '--eval_data', file_path,
        '--per_gpu_batch_size', '1',
        '--n_context', '2',
        '--name', 'predictions',
        '--checkpoint_dir', 'checkpoint'
    ]

    result = subprocess.run(command, capture_output=True, text=True)
    with open("./checkpoint/predictions/predictions.txt","r") as pred_file:
        prediction =  pred_file.read()
    print(prediction)

    return prediction.split("\t")[-1]
 

def copy_project(project,bug,generated_patches):
    # print("Copy project")
    # print(os.getcwd())
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
        with open(REPAIR_PATH+"/"+project+"/"+bug+"/"+"complete.json", 'w') as outfile:
            json.dump(generated_patches, outfile)
        return
    if correctness=="PARTIALLY":
        with open(REPAIR_PATH+"/"+project+"/"+bug+"/"+"FL_"+location+"/"+"IT_"+iteration+"partial.json", 'w') as outfile:
            json.dump(generated_patches, outfile)

    

def repair(generated_patches=[],sample_index=0,COMPLETED=False,sample=None):
    if sample_index >= len(test_samples):
        if COMPLETED:
            write_to_file(project,bug,generated_patches,"COMPLETED",None,None)
            exit()
        return 
    if sample==None:
        sample = test_samples[sample_index]

    iteration =0
    while iteration < NUMBER_OF_ITERATIONS_PER_LOCATION:
        generated_patch = generate_FID(sample)
        copy_project(project,bug,generated_patches)
        apply_patch( REPAIR_PATH+"/"+project+"/"+bug+"/"+CLONE_FILE_NAME,sample, generated_patch)
        correctness_with_error = is_correct(project,bug,generated_patch,sample)
        if correctness_with_error[1] =="COMPLETED":
            generated_patches.append(generated_patch)
            return repair(generated_patches,len(test_samples),True,None)
        
        elif correctness_with_error[1]=="PARTIALLY":
            temp_sample = copy.deepcopy(sample)
            temp_sample["err"]=correctness_with_error[0]
            repair(generated_patches+[generated_patch],sample_index+1,False,temp_sample)

        else:
            temp_sample = copy.deepcopy(sample)
            temp_sample["err"]=correctness_with_error[0]
            repair(generated_patches+[generated_patch],sample_index+1,False)
        iteration+=1

def clear_path(path):
    if os.path.exists(path):
        os.system("rm -rf "+path)
def clear_and_recreate_path(path):
    if os.path.exists(path):
        os.system("rm -rf "+path)
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
    repair()
    
    





