import os
from autogen import AssistantAgent, UserProxyAgent
from repo_documentation.prompt import DOCUMENTATION_PROMPT, \
    DOCUMENTATION_UPDATE_PROMPT, USR_PROMPT
from repo_documentation import utils
from . import config
from code2flow.code2flow import utils as code2flow_utils


def get_documentation(file_path,
                      file_content,
                      additional_docs,
                      user,
                      assistant,
                      output_dir,
                      root_folder,
                      save_debug=False):
    """
    Retrieves documentation for a given file.

    Args:
        file_path (str): The path of the file.
        file_content (str): The content of the file.
        additional_docs (str): Additional documentation to include.
        user (str): The user interacting with the assistant.
        assistant (Assistant): The assistant object.
        output_dir (str): The directory to save debug information.
        root_folder (str): The root folder of the project.
        save_debug (bool, optional): Whether to save debug information. Defaults to False.

    Returns:
        str: The documentation retrieved from the assistant.
    """
    prompt_message = DOCUMENTATION_PROMPT.format(
        file_name=os.path.basename(file_path),
        file_content=file_content,
        root_folder=root_folder,
        additional_docs=additional_docs
    )
    initiate_chat(user, assistant, prompt_message)
    if save_debug:
        utils.save_prompt_debug(
            output_dir, file_path, prompt_message, utils.Mode.CREATE)
    return assistant.last_message()['content']


def get_updated_documentation(file_path,
                             old_file_docs,
                             old_file_content,
                             new_file_content,
                             diff,
                             additional_docs, # TODO: Add additional_docs to the prompt
                             changes,
                             user,
                             assistant,
                             output_dir,
                             save_debug=False):
    """
    Update the file documentation using the old docs, diffs, and additional docs.

    Args:
        file_path (str): The path of the file being updated.
        old_file_docs (str): The old documentation of the file.
        old_file_content (str): The old content of the file.
        new_file_content (str): The new content of the file.
        diff (str): The difference between the old and new content of the file.
        additional_docs (str): Additional documentation to be included.
        user (str): The user interacting with the assistant.
        assistant (Assistant): The assistant object used for communication.
        output_dir (str): The directory to save debug information.
        save_debug (bool, optional): Whether to save debug information. Defaults to False.

    Returns:
        str: The content of the last message from the assistant.
    """
    prompt_message = DOCUMENTATION_UPDATE_PROMPT.format(
        file_name=os.path.basename(file_path),
        old_file_docs=old_file_docs,
        old_file_content=old_file_content,
        new_file_content=new_file_content,
        diff=diff,
        changes=changes
    )
    initiate_chat(user, assistant, prompt_message)
    if save_debug:
        utils.save_prompt_debug(
            output_dir, file_path, prompt_message, utils.Mode.UPDATE)
    return assistant.last_message()['content']


def get_additional_docs_path(file_path, graph, bfs_explore):
    additional_docs = ""
    file_to_calls = code2flow_utils.get_file_to_functions(graph)
    for file_path, calls in file_to_calls.items():
        if file_path == 'EXTERNAL':
            continue
        calls = file_to_calls[file_path]
        additional_docs += get_additional_docs_calls(calls, graph, bfs_explore)
    return additional_docs

def get_additional_docs_calls(calls, graph, bfs_explore):
    additional_docs = ""
    for call_name in calls:
        call = graph[call_name]
        if 'EXTERNAL' in call['file_name']:
            continue
        for callee in bfs_explore[call_name]:
            callee_call = graph[callee]
            additional_docs += f"\nFunction/Class {
                callee_call['name']}:\n{callee_call['content']}\n"
    return additional_docs


def load_assistant_agent():
    # Load the assistant agent for LLM-based documentation generation
    return AssistantAgent(
        name="assistant",
        system_message=USR_PROMPT,
        llm_config=config.llm_config,
        human_input_mode="NEVER"
    )


def load_user_agent():
    # Load the user agent for LLM-based documentation generation
    return UserProxyAgent(
        name="user",
        code_execution_config=False,
    )


def initiate_chat(user: UserProxyAgent, assistant, prompt):
    user.initiate_chat(
        assistant,
        message=prompt,
        max_turns=1,
        silent=True
    )


def last_message(assistant):
    return assistant.last_message()['content']
