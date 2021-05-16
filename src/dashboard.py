import streamlit as st
import pandas as pd
import nltk
import mysql.connector
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from viz.filter_lists import help_words, stop_words
from db.connector import db_instance
import plotly.express as px
import datetime
import re
import dataframe_image as dfi
#nltk.download('punkt') # needs to be run the first time the code is run on your machine, but can be commented out afterwards

#### TEXT PROCESSING FUNCTIONS ####

def remove_emoji(string):
    #Removes emojis from strings
    emoji_pattern = re.compile("["
                           u"\U0001F600-\U0001F64F"  # emoticons
                           u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                           u"\U0001F680-\U0001F6FF"  # transport & map symbols
                           u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                           u"\U00002702-\U000027B0"
                           u"\U000024C2-\U0001F251"
                           "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', string)

@st.cache
def unfiltered_frequency(messages):
    # takes in list of messages and returns a dataframe of words and their frequencies
    token_list = []
    for message in messages:
        message = remove_emoji(message)
        message_tokens = nltk.tokenize.word_tokenize(message) #getting tokens from all chat messages
        for token in message_tokens:
            if token in stop_words: #takes out stop words
                continue
            if token.isdigit(): #makes sure user ids aren't being collected
                continue
            token_list.append(token)

    word_dist = nltk.FreqDist(token_list)
    result = pd.DataFrame(word_dist.most_common(), columns=['Word', 'Frequency'])
    return result

@st.cache
def help_messages_frequency(messages):
    #getting tokens from help messages
    token_list = []
    for message in messages:
        message = remove_emoji(message)
        for i in help_words: #going through each word in help_words list
            if i in message: #checking if helpword is in the message
                message_tokens = nltk.tokenize.word_tokenize(message)
                for token in message_tokens:
                    if token.isdigit(): #makes sure user ids aren't being collected
                        continue
                    if token in stop_words or token in help_words: #taking out stop words and help keywords
                        continue
                    token_list.append(token)

    word_dist = nltk.FreqDist(token_list)
    result = pd.DataFrame(word_dist.most_common(), columns=['Word', 'Frequency'])
    return result    

def make_wordcloud(df):
    # takes in a dataframe
    text = " ". join(word for word in df['message_content'].astype(str)) 
    wc_caption = 'Wordcloud built from analysis of  '+ str(len(text)) + ' words. The size of the word indicates the frequency - so the larger the word, the more frequently it occurs in the data.'

    wordcloud = WordCloud(stopwords=stop_words, background_color="white", width=800, height=600, collocations=False).generate(text)

    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    plt.savefig('wc.png')

    return wc_caption
#####################################


####### DB Connection #######
db_instance.connect()
cx = db_instance.get_connect()

query = "SELECT c.message_id, c.user_id, c.user_name, c.channel_id as c_channel_id, c.message_content, c.created_on, d.channel_id as d_channel_id, d.channel_name FROM clean_message as c JOIN discord_channel as d ON c.channel_id=d.channel_id"

raw_df = pd.read_sql_query(query, cx)
raw_df['simple_date'] = raw_df['created_on'].dt.date # adds 'simple date' column to dataframe with datetime.date conversions
################################


##### Dashboard code ######

## sidebar input parameters
channel_listing = ['All']

for x in raw_df['channel_name'].unique():
    channel_listing.append(x)

channel_options = st.sidebar.multiselect(label="Which channel(s) would you like to look at?", options=channel_listing, default="All", help="If nothing selected, results will be based on entire server data") # returns a list
genesis = datetime.date(2021, 1, 1) # default value of start_date date picker
start_date = st.sidebar.date_input(label="Choose a start date:", value=genesis) #returns datetime.date 
end_date = st.sidebar.date_input(label="Choose an end date:") # returns datetime.date

st.sidebar.markdown("## Export whole dashboard")
st.sidebar.markdown("Dashboard can be saved as a pdf using your browser 'Print' option. For best results, use Google Chrome.") 
#export_pdf = st.sidebar.checkbox(label="Tidy for printing")
st.sidebar.markdown("## Download individual visualisations")
st.sidebar.markdown("1. Wordcloud can be downloaded by right-clicking and selecting the download option.")
st.sidebar.markdown("2. Graphs can be downloaded by hovering over them and clicking the camera icon that appears in the top right corner.")
st.sidebar.markdown("3. To download the keyword frequency tables, select which one to download below and follow the instructions.")

## dataframe queries and filtering
df_channel = raw_df['channel_name'].isin(channel_options)

if 'All' in channel_options or channel_options == []:
    mid_df = raw_df
    selected_range = (mid_df['simple_date'] >= start_date) & (mid_df['simple_date'] <= end_date) 
    current_df = mid_df[selected_range] # filtering df for date range
else:
    mid_df = raw_df[df_channel] # filtering df for selected channels
    selected_range = (mid_df['simple_date'] >= start_date) & (mid_df['simple_date'] <= end_date) 
    current_df = mid_df[selected_range] # filtering df for date range

wc_caption = make_wordcloud(current_df) #generating wordcloud
chat_messages = current_df['message_content'].str.lower() 
unfiltered_msgs = unfiltered_frequency(chat_messages) # returns word frequency df from all messages
help_msgs = help_messages_frequency(chat_messages) # returns word frequency df from help messages
total_msgs = current_df['message_id'].nunique()

## main page
st.title("Discord Data Analysis")
st.write("A dashboard for displaying message and channel metrics for Instatute's Discord server.")
st.write("Currently analysing ", total_msgs, " messages.")

container1 = st.beta_container()
container2 = st.beta_container()
container3 = st.beta_container()
container4 = st.beta_container()

with container1:
    st.header("Wordcloud")
    st.image('wc.png', caption=wc_caption)
    st.markdown("""---""")

with container2:
    st.header("Top Keywords")
    col41, col42 = st.beta_columns(2)
    amount = st.slider(min_value=10, max_value=50, value=10, step=5, label="Select number of words to display.")
    with col41:
        st.subheader("All messages")
        dfi.export(unfiltered_msgs.head(amount), 'df1.png') 
    
        st.dataframe(unfiltered_msgs.head(amount), height=600)
        st.write("The top keywords calculated from all messages.")

        dl_df1 = st.sidebar.checkbox(label="All messages keywords", key="download-allmsgs")
        if dl_df1:
            st.sidebar.write("Please right click and save the following image. Untick the box once finished.")
            st.sidebar.image('df1.png')
 
    with col42:
        st.subheader("Help messages")
        dfi.export(help_msgs.head(amount), 'df2.png') 

        st.dataframe(help_msgs.head(amount), height=600)
        st.write("The top keywords calculated from messages categorised as requests for help.")

        dl_df2 = st.sidebar.checkbox(label="Help messages keywords", key="download-helpmsgs")
        if dl_df2:
            st.sidebar.write("Please right click and save the following image. Untick the box once finished.")
            st.sidebar.image('df2.png')

    st.markdown("""---""")

with container3:
    st.header("Channel metrics")
    
    #Proportion of messages by channel(s) as %
    fig1 = px.pie(data_frame=current_df, values='c_channel_id', names='channel_name', title='Channel popularity (%)')
    st.plotly_chart(fig1)
    st.write('The pie chart displays the number of messages contributed by each selected channel. This is an indirect method of calculating topic frequency, assuming that a greater percentage of messages indicates more discussion in that channel.')
    
    #Volume of channel messages in date range
    date_filtered = current_df.groupby('simple_date')['message_id'].nunique().reset_index() # returns a dataframe grouped by simple_date with calculated message frequency per date
    fig2 = px.scatter(date_filtered, x='simple_date', y="message_id", labels={'simple_date': 'Date', 'message_id': 'Number of messages'}, title='Volume of messages over date range')
    st.plotly_chart(fig2)
    st.write('The marks indicate the number of messages posted on the given date. The trend over time may be correlated with real-world events such as upcoming assignments or the introduction of a new subject in class.')

    #Top 10 posters in selected channels as percent
    top10 = current_df['user_name'].value_counts(normalize="true")*100
    fig3 = px.bar(top10.head(10), title='Top 10 Posters (%)', labels={'index': 'Username', 'value': 'Contributions as %'})
    st.plotly_chart(fig3)
    st.write("--------")

with container4:
    st.header("Experimental summarisation with NLP")
    st.markdown("The following is a set of sentences that summarise what is being discussed in the selected channel within the selected date range. By default it is turned off due to performance issues. To see it, please tick the box.")
    show_nlp = st.checkbox(label="Show experimental NLP")
    if show_nlp: #displays nlp prototypes if toggled on
        from viz.nlp_summary import sumy_nlp
        all_messages = ""
        for line in chat_messages:
            all_messages = all_messages + line + ". " 

        nlp_result = sumy_nlp(all_messages)
        
        count = 1
        summary = ""
        for sentence in nlp_result:
            st.markdown(str(count) + '. ' + str(sentence))
            summary += str(sentence).capitalize() + " "
            count += 1
        st.markdown("_" + summary + "_")