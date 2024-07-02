import os
import sys
import time
from autogen import AssistantAgent, UserProxyAgent
from prompt import DOCUMENTATION_PROMPT, USR_PROMPT

sys.path.append(os.path.abspath(
    os.path.join(os.path.dirname(__file__), './../')))

import config
from cache.docs_cache import DocsCache
from code2flow.code2flow import utils

class RepoDocumentation():
    def __init__(self, root_folder, output_dir='code2flow_output'):
        self.root_folder = root_folder
        self.output_dir = output_dir
        self.assistant = self._load_assistant_agent()
        self.user = self._load_user_agent()

    def run(self):
        print("Starting the documentation generation process...")
        start_time = time.time()

        # 1. Generate graph (call_graph.json and cache.json)
        utils.generate_graph(self.root_folder, self.output_dir)
        graph = utils.get_call_graph(self.output_dir)

        # 2. Build mapping of a file to the functions called within them
        file_to_calls = utils.get_file_to_functions(graph)

        # 3. Build BFS exploration of the call graph
        bfs_explore = utils.explore_call_graph(graph)

        # 4. Prepare cache, where we will map file paths to their respective documentation
        cache = DocsCache()

        # 5. Generate documentation for each file and function within
        for file_path, calls in file_to_calls.items():
            print(f"Generating documentation for file={file_path}")
            if file_path == 'EXTERNAL':
                continue

            additional_docs = self._get_additional_docs(
                calls, graph, bfs_explore)
            file_content = self._read_file_content(file_path)
            file_docs = self._generate_file_docs(
                file_path, file_content, additional_docs)
            docs_output_filepath = self._write_file_docs(file_path, file_docs)

            # 6. Add the generated documentation to the cache (file_path -> docs_output_filepath)
            cache.add(file_path, docs_output_filepath)

        # 7. Save cache to a file
        utils.write_json(f'{self.output_dir}/cache.json', cache.to_dict())

        total = round(time.time() - start_time, 3)
        print(f"Total time taken to execute doc generation: {total}s.")

    def _load_assistant_agent(self):
        return AssistantAgent(
            name="assistant",
            system_message=USR_PROMPT,
            llm_config=config.llm_config,
            human_input_mode="NEVER"
        )

    def _load_user_agent(self):
        return UserProxyAgent(
            name="user",
            code_execution_config=False,
        )

    def _get_additional_docs(self, calls, graph, bfs_explore):
        additional_docs = ""
        for call_name in calls:
            call = graph[call_name]
            if 'EXTERNAL' in call['file_name']:
                continue
            for callee in bfs_explore[call_name]:
                callee_call = graph[callee]
                additional_docs += f"\nFunction/Class {callee_call['name']}:\n{callee_call['content']}\n"
        return additional_docs

    def _read_file_content(self, file_path):
        print(f"Reading file: {file_path}")
        with open(file_path, 'r') as file:
            return file.read()

    def _generate_file_docs(self, file_path, file_content, additional_docs):
        prompt_message = DOCUMENTATION_PROMPT.format(
            file_name=os.path.basename(file_path),
            file_content=file_content,
            root_folder=self.root_folder,
            additional_docs=additional_docs
        )

        self.user.initiate_chat(
            self.assistant,
            message=prompt_message,
            max_turns=1,
            silent=True
        )

        # Save the prompt message to a file (debugging purposes)
        file_name = self.output_dir + "/" + \
            os.path.basename(file_path) + ".txt"
        with open(file_name, 'w') as file:
            file.write(prompt_message)

        return self.assistant.last_message()['content']

    def _write_file_docs(self, file_path, docs) -> str:
        # Generate the output file path based on the input file path
        relative_path = os.path.relpath(file_path, self.root_folder)
        output_file_path = os.path.join(self.output_dir, relative_path)
        output_dir = os.path.dirname(output_file_path)
        os.makedirs(output_dir, exist_ok=True)

        # Add .md extension to the output file
        output_file_path += ".md"

        # Write the documentation to the output file
        with open(output_file_path, 'w') as file:
            file.write(docs)
        return output_file_path


repo_doc = RepoDocumentation(
    root_folder='../code2flow/projects/users',
    output_dir='./../code2flow_output_users')
repo_doc.run()
